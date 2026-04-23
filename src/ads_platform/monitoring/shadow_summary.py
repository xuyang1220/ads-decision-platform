from __future__ import annotations

import argparse
import json
from typing import Any


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def build_alerts(summary_payload: dict[str, Any], attainment_tol: float, overlap_floor: float) -> list[dict[str, Any]]:
    summary = summary_payload.get("summary", {})
    budget_summary = summary.get("budget_summary", {})
    auction_summary = summary.get("auction_summary", {})
    controller_summary = summary.get("controller_summary", {})
    time_bucket_tail = summary.get("time_bucket_tail", [])

    alerts: list[dict[str, Any]] = []

    spend_attainment_ratio = _safe_float(budget_summary.get("spend_attainment_ratio"))
    if abs(spend_attainment_ratio - 1.0) > attainment_tol:
        alerts.append(
            {
                "severity": "warn",
                "metric": "spend_attainment_ratio",
                "message": f"Spend attainment ratio {spend_attainment_ratio:.4f} is outside tolerance ±{attainment_tol:.2f}.",
            }
        )

    overlap = _safe_float(auction_summary.get("avg_winner_overlap_jaccard"))
    if overlap < overlap_floor:
        alerts.append(
            {
                "severity": "warn",
                "metric": "avg_winner_overlap_jaccard",
                "message": f"Shadow-vs-inferred-prod winner overlap {overlap:.4f} is below floor {overlap_floor:.2f}.",
            }
        )

    num_clipped = int(controller_summary.get("num_clipped_updates", 0))
    num_updates = max(1, int(controller_summary.get("num_updates", 0)))
    clipped_rate = num_clipped / num_updates
    if clipped_rate > 0.30:
        alerts.append(
            {
                "severity": "warn",
                "metric": "controller_clipped_rate",
                "message": f"Controller clipped on {clipped_rate:.1%} of updates.",
            }
        )

    if time_bucket_tail:
        latest = time_bucket_tail[-1]
        realized_to_target = _safe_float(latest.get("realized_to_target_ratio"))
        if abs(realized_to_target - 1.0) > attainment_tol:
            alerts.append(
                {
                    "severity": "warn",
                    "metric": "latest_realized_to_target_ratio",
                    "message": f"Latest cumulative realized/target ratio {realized_to_target:.4f} is outside tolerance ±{attainment_tol:.2f}.",
                }
            )

    if not alerts:
        alerts.append(
            {
                "severity": "info",
                "metric": "shadow_health",
                "message": "No major shadow-mode alerts fired.",
            }
        )
    return alerts


def compact_report(summary_payload: dict[str, Any], alerts: list[dict[str, Any]]) -> dict[str, Any]:
    summary = summary_payload.get("summary", {})
    budget_summary = summary.get("budget_summary", {})
    auction_summary = summary.get("auction_summary", {})
    controller_summary = summary.get("controller_summary", {})
    return {
        "config": summary_payload.get("config", {}),
        "headline_metrics": {
            "realized_spend": _safe_float(budget_summary.get("realized_spend")),
            "budget": _safe_float(budget_summary.get("budget")),
            "spend_attainment_ratio": _safe_float(budget_summary.get("spend_attainment_ratio")),
            "avg_winner_overlap_jaccard": _safe_float(auction_summary.get("avg_winner_overlap_jaccard")),
            "avg_pacing_multiplier": _safe_float(controller_summary.get("avg_pacing_multiplier")),
            "num_controller_updates": int(controller_summary.get("num_updates", 0)),
        },
        "alerts": alerts,
        "time_bucket_tail": summary.get("time_bucket_tail", []),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize shadow-run output into dashboard-friendly alerts")
    parser.add_argument("--shadow-output-path", required=True)
    parser.add_argument("--attainment-tol", type=float, default=0.10)
    parser.add_argument("--overlap-floor", type=float, default=0.20)
    args = parser.parse_args()

    with open(args.shadow_output_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    alerts = build_alerts(payload, attainment_tol=args.attainment_tol, overlap_floor=args.overlap_floor)
    report = compact_report(payload, alerts)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
