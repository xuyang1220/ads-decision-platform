from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(slots=True)
class TimeBucketDiagnostic:
    bucket_index: int
    bucket_start_ts_ms: int
    bucket_end_ts_ms: int
    num_auctions: int
    num_winners: int

    period_realized_spend: float
    period_predicted_spend: float
    period_target_spend: float

    cumulative_realized_spend: float
    cumulative_predicted_spend: float
    cumulative_target_spend: float

    realized_minus_target: float
    predicted_minus_target: float

    avg_pacing_multiplier: float
    avg_throttle_prob: float

    realized_to_target_ratio: float
    predicted_to_target_ratio: float


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def build_time_bucketed_pacing_diagnostics(
    per_auction: list[dict[str, Any]],
    num_buckets: int = 20,
) -> list[dict[str, Any]]:
    if not per_auction:
        return []

    auctions = sorted(
        per_auction,
        key=lambda x: int(x.get("timestamp_ms", x.get("auction_timestamp_ms", 0))),
    )

    timestamps = [
        int(a.get("timestamp_ms", a.get("auction_timestamp_ms", 0)))
        for a in auctions
    ]
    min_ts = min(timestamps)
    max_ts = max(timestamps)

    if max_ts <= min_ts:
        max_ts = min_ts + 1

    bucket_rows: list[list[dict[str, Any]]] = [[] for _ in range(num_buckets)]

    for auction in auctions:
        ts = int(auction.get("timestamp_ms", auction.get("auction_timestamp_ms", 0)))
        frac = (ts - min_ts) / (max_ts - min_ts)
        idx = min(num_buckets - 1, max(0, int(frac * num_buckets)))
        bucket_rows[idx].append(auction)

    results: list[TimeBucketDiagnostic] = []

    cumulative_realized = 0.0
    cumulative_predicted = 0.0
    cumulative_target = 0.0

    for idx, rows in enumerate(bucket_rows):
        bucket_start_ts = int(min_ts + (idx / num_buckets) * (max_ts - min_ts))
        bucket_end_ts = int(min_ts + ((idx + 1) / num_buckets) * (max_ts - min_ts))

        if not rows:
            diag = TimeBucketDiagnostic(
                bucket_index=idx,
                bucket_start_ts_ms=bucket_start_ts,
                bucket_end_ts_ms=bucket_end_ts,
                num_auctions=0,
                num_winners=0,
                period_realized_spend=0.0,
                period_predicted_spend=0.0,
                period_target_spend=cumulative_target - cumulative_target,
                cumulative_realized_spend=cumulative_realized,
                cumulative_predicted_spend=cumulative_predicted,
                cumulative_target_spend=cumulative_target,
                realized_minus_target=cumulative_realized - cumulative_target,
                predicted_minus_target=cumulative_predicted - cumulative_target,
                avg_pacing_multiplier=0.0,
                avg_throttle_prob=0.0,
                realized_to_target_ratio=(cumulative_realized / cumulative_target) if cumulative_target > 0 else 0.0,
                predicted_to_target_ratio=(cumulative_predicted / cumulative_target) if cumulative_target > 0 else 0.0,
            )
            results.append(diag)
            continue

        period_realized = 0.0
        period_predicted = 0.0
        period_target = 0.0
        num_winners = 0

        pacing_sum = 0.0
        throttle_sum = 0.0
        pacing_count = 0

        for auction in rows:
            period_realized += _safe_float(auction.get("realized_spend", 0.0))
            period_predicted += _safe_float(auction.get("predicted_spend", 0.0))
            period_target += _safe_float(
                auction.get("target_spend_increment", auction.get("target_spend_delta", 0.0))
            )

            decision_logs = auction.get("decision_logs", [])
            for row in decision_logs:
                if row.get("selected"):
                    num_winners += 1
                    pacing_sum += _safe_float(row.get("pacing_multiplier", 0.0))
                    throttle_sum += _safe_float(row.get("throttle_prob", 0.0))
                    pacing_count += 1

        cumulative_realized += period_realized
        cumulative_predicted += period_predicted
        cumulative_target += period_target

        avg_pacing = pacing_sum / pacing_count if pacing_count > 0 else 0.0
        avg_throttle = throttle_sum / pacing_count if pacing_count > 0 else 0.0

        diag = TimeBucketDiagnostic(
            bucket_index=idx,
            bucket_start_ts_ms=bucket_start_ts,
            bucket_end_ts_ms=bucket_end_ts,
            num_auctions=len(rows),
            num_winners=num_winners,
            period_realized_spend=period_realized,
            period_predicted_spend=period_predicted,
            period_target_spend=period_target,
            cumulative_realized_spend=cumulative_realized,
            cumulative_predicted_spend=cumulative_predicted,
            cumulative_target_spend=cumulative_target,
            realized_minus_target=cumulative_realized - cumulative_target,
            predicted_minus_target=cumulative_predicted - cumulative_target,
            avg_pacing_multiplier=avg_pacing,
            avg_throttle_prob=avg_throttle,
            realized_to_target_ratio=(cumulative_realized / cumulative_target) if cumulative_target > 0 else 0.0,
            predicted_to_target_ratio=(cumulative_predicted / cumulative_target) if cumulative_target > 0 else 0.0,
        )
        results.append(diag)

    return [asdict(x) for x in results]