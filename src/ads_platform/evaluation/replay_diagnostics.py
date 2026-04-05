from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any


@dataclass(slots=True)
class CalibrationBucket:
    bucket_index: int
    bucket_start: float
    bucket_end: float
    num_selected: int
    predicted_clicks: float
    observed_clicks: int
    avg_predicted_ctr: float
    observed_ctr: float
    calibration_gap: float
    avg_effective_bid: float


def _selected_rows(per_auction: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for auction in per_auction:
        for row in auction.get('decision_logs', []):
            if row.get('selected'):
                rows.append(row)
    return rows


def build_calibration_table(per_auction: list[dict[str, Any]], num_buckets: int = 10) -> list[CalibrationBucket]:
    rows = _selected_rows(per_auction)
    print("num_selected_rows =", len(rows))
    print("sample_selected_row_keys =", rows[0].keys())
    print("sample_selected_row =", rows[0])
    if not rows:
        return []

    buckets: list[list[dict[str, Any]]] = [[] for _ in range(num_buckets)]
    for row in rows:
        p = float(row.get('pctr_calibrated', 0.0))
        idx = min(num_buckets - 1, max(0, int(math.floor(p * num_buckets))))
        buckets[idx].append(row)

    table: list[CalibrationBucket] = []
    for idx, bucket_rows in enumerate(buckets):
        if not bucket_rows:
            continue
        n = len(bucket_rows)
        predicted_clicks = sum(float(r.get('pctr_calibrated', 0.0)) for r in bucket_rows)
        observed_clicks = sum(int(r.get('observed_clicked', 0)) for r in bucket_rows)
        avg_pred = predicted_clicks / n
        observed_ctr = observed_clicks / n
        avg_bid = sum(float(r.get('bid_effective', 0.0)) for r in bucket_rows) / n
        table.append(
            CalibrationBucket(
                bucket_index=idx,
                bucket_start=idx / num_buckets,
                bucket_end=(idx + 1) / num_buckets,
                num_selected=n,
                predicted_clicks=predicted_clicks,
                observed_clicks=observed_clicks,
                avg_predicted_ctr=avg_pred,
                observed_ctr=observed_ctr,
                calibration_gap=predicted_clicks - observed_clicks,
                avg_effective_bid=avg_bid,
            )
        )
    return table


def build_predicted_vs_observed(summary: Any) -> dict[str, float]:
    predicted = float(getattr(summary, 'predicted_clicks', 0.0))
    observed = float(getattr(summary, 'observed_clicks_on_selected', 0.0))
    return {
        'predicted_clicks': predicted,
        'observed_clicks': observed,
        'absolute_gap': predicted - observed,
        'relative_gap': ((predicted - observed) / observed) if observed else 0.0,
        'prediction_to_observation_ratio': (predicted / observed) if observed else 0.0,
    }


def build_policy_row(name: str, summary: Any) -> dict[str, float | int | str]:
    num_winners = int(getattr(summary, 'num_winners', 0))
    observed_clicks = float(getattr(summary, 'observed_clicks_on_selected', 0.0))
    realized_spend = float(getattr(summary, 'realized_spend', 0.0))
    predicted_clicks = float(getattr(summary, 'predicted_clicks', 0.0))
    return {
        'policy': name,
        'num_auctions': int(getattr(summary, 'num_auctions', 0)),
        'num_winners': num_winners,
        'predicted_clicks': predicted_clicks,
        'observed_clicks': int(observed_clicks),
        'realized_spend': realized_spend,
        'avg_predicted_ctr_selected': float(getattr(summary, 'avg_predicted_ctr_selected', 0.0)),
        'observed_ctr_selected': (observed_clicks / num_winners) if num_winners else 0.0,
        'avg_effective_bid_selected': float(getattr(summary, 'avg_effective_bid_selected', 0.0)),
        'spend_per_observed_click': (realized_spend / observed_clicks) if observed_clicks else 0.0,
        'predicted_vs_observed_ratio': (predicted_clicks / observed_clicks) if observed_clicks else 0.0,
    }
