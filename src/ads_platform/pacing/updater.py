from __future__ import annotations

from dataclasses import dataclass

from ads_platform.pacing.desired_curve import DesiredSpendCurve
from ads_platform.pacing.state import ControllerState, SpendSnapshot
from ads_platform.schemas.pacing import BudgetState


@dataclass(slots=True)
class BudgetTracker:
    entity_id: str
    date: str
    budget_amount: float
    desired_curve: DesiredSpendCurve
    spend_so_far: float = 0.0
    observed_clicks: int = 0

    def minute_of_day(self, timestamp_ms: int) -> int:
        return (timestamp_ms // 60000) % 1440

    def snapshot(self, timestamp_ms: int) -> SpendSnapshot:
        minute = self.minute_of_day(timestamp_ms)
        return SpendSnapshot(
            timestamp_ms=timestamp_ms,
            spend_so_far=self.spend_so_far,
            target_spend_so_far=self.desired_curve.target_spend(minute, self.budget_amount),
            budget_amount=self.budget_amount,
            observed_clicks=self.observed_clicks,
            debug={"minute_of_day": minute},
        )

    def apply_observation(self, spend_delta: float, clicks_delta: int) -> None:
        self.spend_so_far += float(spend_delta)
        self.observed_clicks += int(clicks_delta)

    def to_budget_state(self, controller_state: ControllerState, timestamp_ms: int) -> BudgetState:
        snapshot = self.snapshot(timestamp_ms)
        return BudgetState(
            entity_id=self.entity_id,
            date=self.date,
            budget_amount=self.budget_amount,
            spend_so_far=snapshot.spend_so_far,
            target_spend_so_far=snapshot.target_spend_so_far,
            pacing_multiplier=controller_state.pacing_multiplier,
            throttle_prob=controller_state.throttle_prob,
            shadow_lambda=controller_state.shadow_lambda,
            last_update_ts_ms=controller_state.last_update_ts_ms,
            stale=controller_state.stale,
            debug={**controller_state.debug, **snapshot.debug},
        )
