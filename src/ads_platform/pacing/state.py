from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SpendSnapshot:
    timestamp_ms: int
    spend_so_far: float
    target_spend_so_far: float
    budget_amount: float
    observed_clicks: int = 0
    debug: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ControllerState:
    entity_id: str
    date: str
    pacing_multiplier: float = 1.0
    throttle_prob: float = 1.0
    shadow_lambda: float | None = None
    last_update_ts_ms: int = 0
    stale: bool = False
    integral_error: float = 0.0
    debug: dict[str, Any] = field(default_factory=dict)
