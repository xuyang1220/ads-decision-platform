from __future__ import annotations

from typing import Any


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
        "prediction_gap": predicted_spend - realized_spend,
        "avg_realized_spend_per_winner": (realized_spend / num_selected) if num_selected else 0.0,
        "fallback_rate": (fallback_count / num_selected) if num_selected else 0.0,
    }
