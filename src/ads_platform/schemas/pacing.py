from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PacingDirective(BaseModel):
    pacing_multiplier: float
    throttle_prob: float
    shadow_lambda: float | None = None
    reason: str = ""
    debug: dict[str, Any] = Field(default_factory=dict)


class BudgetState(BaseModel):
    entity_id: str
    date: str
    budget_amount: float
    spend_so_far: float
    target_spend_so_far: float
    pacing_multiplier: float
    throttle_prob: float
    shadow_lambda: float | None = None
    last_update_ts_ms: int
    stale: bool = False
    debug: dict[str, Any] = Field(default_factory=dict)

    @property
    def current_directive(self) -> PacingDirective:
        return PacingDirective(
            pacing_multiplier=self.pacing_multiplier,
            throttle_prob=self.throttle_prob,
            shadow_lambda=self.shadow_lambda,
            reason="state_snapshot",
            debug={"stale": self.stale},
        )
