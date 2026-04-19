from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
from typing import Any, Iterable

from ads_platform.landscape.artifact import EmpiricalLandscapeArtifact
from ads_platform.landscape.empirical import EmpiricalTable, SegmentCurve
from ads_platform.landscape.fallback import candidate_fallback_keys
from ads_platform.schemas.landscape import LandscapeContext


@dataclass(slots=True)
class FitRow:
    key: str
    bid: float
    won: int
    cost: float


@dataclass(slots=True)
class FitConfig:
    min_rows_per_key: int = 20
    num_bid_bins: int = 6
    include_segment_keys: bool = True
    include_adgroup_keys: bool = False
    include_campaign_keys: bool = False
    include_channel_keys: bool = True
    include_global_key: bool = True
    default_curve: SegmentCurve = field(default_factory=lambda: SegmentCurve(slope=1.2, midpoint=1.0, cost_fraction=0.7))
    model_version: str = "fitted_empirical_v1"


def _context_from_candidate(request: dict[str, Any], candidate: dict[str, Any]) -> LandscapeContext:
    extra = dict(candidate.get("extra", {}))
    return LandscapeContext(
        campaign_id=str(candidate.get("campaign_id", "unknown_campaign")),
        adgroup_id=str(candidate.get("adgroup_id", candidate.get("campaign_id", "unknown_campaign"))),
        segment_id=(None if extra.get("segment_id") is None else int(extra.get("segment_id"))),
        channel=str(request.get("placement", "unknown")),
        extra={},
    )


def _allowed_level(level: str, config: FitConfig) -> bool:
    if level.startswith("adgroup"):
        return config.include_adgroup_keys
    if level.startswith("campaign"):
        return config.include_campaign_keys
    if level.startswith("channel"):
        return config.include_channel_keys
    if level == "global":
        return config.include_global_key
    return False


def _iter_fit_rows_from_jsonl(path: str | Path, config: FitConfig) -> Iterable[FitRow]:
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            request = dict(payload.get("request", {}))
            candidates = list(payload.get("candidates", []))
            outcomes = list(payload.get("outcomes", []))
            observed = payload.get("observed", {})

            if outcomes and len(outcomes) != len(candidates):
                raise ValueError(
                    f"Length mismatch at line {line_no}: {len(candidates)} candidates vs {len(outcomes)} outcomes"
                )

            clicked_ad_ids = {str(x) for x in observed.get("clicked_ad_ids", [])}
            spend_by_ad_id = {str(k): float(v) for k, v in dict(observed.get("spend_by_ad_id", {})).items()}

            for idx, candidate in enumerate(candidates):
                ad_id = str(candidate["ad_id"])
                context = _context_from_candidate(request, candidate)
                bid = float(candidate.get("base_bid", 0.0))

                if outcomes:
                    outcome = outcomes[idx]
                    # If explicit won is present, trust it. Otherwise infer win from positive cost/price.
                    won = int(outcome.get("won", 1 if float(outcome.get("price", outcome.get("cost", 0.0))) > 0 else 0))
                    cost = float(outcome.get("price", outcome.get("cost", 0.0)))
                else:
                    won = int(ad_id in clicked_ad_ids or ad_id in spend_by_ad_id)
                    cost = float(spend_by_ad_id.get(ad_id, candidate.get("realized_spend", 0.0)))

                for level, key in candidate_fallback_keys(context):
                    if not _allowed_level(level, config):
                        continue
                    if level.endswith("segment") and not config.include_segment_keys:
                        continue
                    yield FitRow(key=key, bid=bid, won=won, cost=cost)


def _make_monotone(values: list[float]) -> list[float]:
    out: list[float] = []
    running = float("-inf")
    for value in values:
        running = max(running, float(value))
        out.append(running)
    return out


def _quantile_bins(values: list[float], num_bins: int) -> list[float]:
    if not values:
        return [0.0, 1.0]
    xs = sorted(float(v) for v in values)
    if len(xs) == 1:
        x = xs[0]
        return [x, x + 1e-6]
    edges: list[float] = []
    for i in range(num_bins):
        p = i / max(num_bins - 1, 1)
        idx = min(len(xs) - 1, int(round(p * (len(xs) - 1))))
        edges.append(xs[idx])
    # dedupe while preserving order
    deduped: list[float] = []
    for x in edges:
        if not deduped or x > deduped[-1]:
            deduped.append(x)
    if len(deduped) == 1:
        deduped.append(deduped[0] + 1e-6)
    return deduped


def _fit_table(rows: list[FitRow], num_bid_bins: int) -> EmpiricalTable:
    bids = [row.bid for row in rows]
    grid = _quantile_bins(bids, num_bid_bins)
    bucket_rows: list[list[FitRow]] = [[] for _ in range(len(grid))]
    for row in rows:
        idx = 0
        while idx < len(grid) - 1 and row.bid > grid[idx]:
            idx += 1
        bucket_rows[idx].append(row)

    bids_out: list[float] = []
    win_probs: list[float] = []
    expected_costs: list[float] = []
    for fallback_bid, bucket in zip(grid, bucket_rows):
        if bucket:
            bid_value = sum(r.bid for r in bucket) / len(bucket)
            win_prob = sum(r.won for r in bucket) / len(bucket)
            total_won = sum(r.won for r in bucket)
            if total_won > 0:
                expected_cost = sum(r.cost for r in bucket if r.won) / total_won
            else:
                expected_cost = 0.0
        else:
            bid_value = float(fallback_bid)
            win_prob = 0.0
            expected_cost = 0.0
        bids_out.append(float(bid_value))
        win_probs.append(float(win_prob))
        expected_costs.append(float(expected_cost))

    win_probs = _make_monotone(win_probs)
    expected_costs = _make_monotone(expected_costs)
    return EmpiricalTable(bids=bids_out, win_probs=win_probs, expected_costs=expected_costs)


def fit_empirical_artifact_from_jsonl(path: str | Path, config: FitConfig | None = None) -> EmpiricalLandscapeArtifact:
    config = config or FitConfig()
    grouped: dict[str, list[FitRow]] = {}
    for row in _iter_fit_rows_from_jsonl(path, config):
        grouped.setdefault(row.key, []).append(row)

    tables_by_key: dict[str, EmpiricalTable] = {}
    key_counts: dict[str, int] = {}
    for key, rows in grouped.items():
        key_counts[key] = len(rows)
        if len(rows) < config.min_rows_per_key:
            continue
        tables_by_key[key] = _fit_table(rows, num_bid_bins=config.num_bid_bins)

    metadata = {
        "source_path": str(path),
        "num_rows_total": sum(len(v) for v in grouped.values()),
        "num_keys_seen": len(grouped),
        "num_tables_written": len(tables_by_key),
        "min_rows_per_key": config.min_rows_per_key,
        "num_bid_bins": config.num_bid_bins,
        "rows_by_key": key_counts,
    }
    return EmpiricalLandscapeArtifact(
        model_version=config.model_version,
        tables_by_key=tables_by_key,
        default_curve=config.default_curve,
        metadata=metadata,
    )
