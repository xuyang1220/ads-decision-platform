from __future__ import annotations

from typing import Any


def build_pacing_summary(controller_updates: list[dict[str, Any]]) -> dict[str, float | int]:
    if not controller_updates:
        return {
            "num_updates": 0,
            "avg_pacing_multiplier": 0.0,
            "min_pacing_multiplier": 0.0,
            "max_pacing_multiplier": 0.0,
            "num_clipped_updates": 0,
        }
    multipliers = [float(update.get("pacing_multiplier", 0.0)) for update in controller_updates]
    return {
        "num_updates": len(controller_updates),
        "avg_pacing_multiplier": sum(multipliers) / len(multipliers),
        "min_pacing_multiplier": min(multipliers),
        "max_pacing_multiplier": max(multipliers),
        "num_clipped_updates": sum(1 for update in controller_updates if bool(update.get("was_clipped", False))),
    }
