from __future__ import annotations

from typing import Any
from collections import defaultdict
import numpy as np

def build_spend_by_bid_bucket(per_auction: list[dict[str, Any]], num_buckets: int = 5):
    rows = []
    for auction in per_auction:
        for row in auction.get("decision_logs", []):
            if row.get("selected"):
                rows.append(row)

    if not rows:
        return []

    # Find max bid to normalize buckets
    max_bid = max(float(r.get("bid_effective", 0.0)) for r in rows)
    if max_bid <= 0:
        return []

    buckets = [defaultdict(float) for _ in range(num_buckets)]
    counts = [0] * num_buckets

    bids = sorted(r["bid_effective"] for r in rows)
    quantiles = np.quantile(bids, np.linspace(0, 1, num_buckets + 1))

    for r in rows:
        bid = float(r.get("bid_effective", 0.0))
        pred_cost = float(r.get("estimated_cost", 0.0))
        real_cost = float(r.get("realized_spend", 0.0))
        pctr = float(r.get("pctr_calibrated", 0.0))

        # uniform bucket by bid
        # idx = min(num_buckets - 1, int((bid / max_bid) * num_buckets))

        # bucket quantiles
        bucket_idx = np.searchsorted(quantiles, bid, side="right") - 1
        idx = max(0, min(bucket_idx, len(quantiles) - 2))

        buckets[idx]["predicted_spend"] += pred_cost
        buckets[idx]["realized_spend"] += real_cost
        buckets[idx]["sum_bid"] += bid
        buckets[idx]["sum_pctr"] += pctr
        counts[idx] += 1

    results = []
    for i in range(num_buckets):
        if counts[i] == 0:
            continue

        pred = buckets[i]["predicted_spend"]
        real = buckets[i]["realized_spend"]

        results.append({
            "bucket_index": i,
            "num_selected": counts[i],
            "predicted_spend": pred,
            "realized_spend": real,
            "predicted_to_realized_ratio": pred / real if real > 0 else 0.0,
            "avg_bid": buckets[i]["sum_bid"] / counts[i],
            "avg_predicted_ctr": buckets[i]["sum_pctr"] / counts[i],
        })

    return results

def build_spend_summary(per_auction: list[dict[str, Any]], budget_amount: float) -> dict[str, float]:
    realized_spend = sum(float(auction.get("realized_spend", 0.0)) for auction in per_auction)
    predicted_spend = sum(
        float(row.get("estimated_cost", 0.0))
        for auction in per_auction
        for row in auction.get("decision_logs", [])
        if row.get("selected")
    )
    num_selected = sum(
        1
        for auction in per_auction
        for row in auction.get("decision_logs", [])
        if row.get("selected")
    )
    fallback_count = sum(
        1
        for auction in per_auction
        for row in auction.get("decision_logs", [])
        if row.get("selected") and row.get("debug", {}).get("landscape_fallback_level") not in (None, "adgroup_segment")
    )
    return {
        "budget": float(budget_amount),
        "predicted_spend": predicted_spend,
        "realized_spend": realized_spend,
        "spend_attainment_ratio": (realized_spend / budget_amount) if budget_amount else 0.0,
        "predicted_to_realized_spend_ratio": (predicted_spend / realized_spend) if realized_spend else 0.0,
        "prediction_gap": predicted_spend - realized_spend,
        "avg_realized_spend_per_winner": (realized_spend / num_selected) if num_selected else 0.0,
        "fallback_rate": (fallback_count / num_selected) if num_selected else 0.0,
    }
