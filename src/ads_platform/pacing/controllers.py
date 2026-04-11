from __future__ import annotations

from ads_platform.common.utils import clip
from ads_platform.pacing.base import BudgetController
from ads_platform.pacing.safety import apply_step_limit, safe_stale_directive
from ads_platform.pacing.state import ControllerState, SpendSnapshot
from ads_platform.schemas.pacing import BudgetState, PacingDirective


class BoundedProportionalController(BudgetController):
    def __init__(
        self,
        kp: float,
        min_multiplier: float = 0.5,
        max_multiplier: float = 1.5,
        stale_throttle_prob: float = 0.5,
        max_step_delta: float = 0.25,
    ):
        self.kp = kp
        self.min_multiplier = min_multiplier
        self.max_multiplier = max_multiplier
        self.stale_throttle_prob = stale_throttle_prob
        self.max_step_delta = max_step_delta

    def update(self, state: BudgetState) -> PacingDirective:
        if state.stale:
            return safe_stale_directive(state, stale_throttle_prob=self.stale_throttle_prob)

        budget_denom = max(state.budget_amount, 1e-9)
        error = state.target_spend_so_far - state.spend_so_far
        normalized_error = error / budget_denom
        raw_mult = state.pacing_multiplier * (1.0 + self.kp * normalized_error)
        bounded = clip(raw_mult, self.min_multiplier, self.max_multiplier)
        mult = apply_step_limit(state.pacing_multiplier, bounded, max_step_delta=self.max_step_delta)
        return PacingDirective(
            pacing_multiplier=mult,
            throttle_prob=state.throttle_prob,
            shadow_lambda=state.shadow_lambda,
            reason="bounded_proportional_update",
            debug={
                "entity_id": state.entity_id,
                "error": error,
                "normalized_error": normalized_error,
                "raw_mult": raw_mult,
                "bounded_mult": bounded,
            },
        )


class BoundedPIController:
    def __init__(
        self,
        kp: float,
        ki: float,
        min_multiplier: float = 0.5,
        max_multiplier: float = 1.5,
        integral_clip: float = 2.0,
        max_step_delta: float = 0.25,
    ):
        self.kp = kp
        self.ki = ki
        self.min_multiplier = min_multiplier
        self.max_multiplier = max_multiplier
        self.integral_clip = integral_clip
        self.max_step_delta = max_step_delta

    def update(self, state: ControllerState, snapshot: SpendSnapshot) -> tuple[PacingDirective, ControllerState]:
        error = snapshot.target_spend_so_far - snapshot.spend_so_far
        normalized_error = error / max(snapshot.budget_amount, 1e-9)
        next_integral = clip(state.integral_error + normalized_error, -self.integral_clip, self.integral_clip)
        raw_multiplier = state.pacing_multiplier * (1.0 + self.kp * normalized_error + self.ki * next_integral)
        bounded = clip(raw_multiplier, self.min_multiplier, self.max_multiplier)
        pacing_multiplier = apply_step_limit(state.pacing_multiplier, bounded, max_step_delta=self.max_step_delta)
        directive = PacingDirective(
            pacing_multiplier=pacing_multiplier,
            throttle_prob=state.throttle_prob,
            shadow_lambda=state.shadow_lambda,
            reason="bounded_pi_update",
            debug={
                "error": error,
                "normalized_error": normalized_error,
                "integral_error": next_integral,
                "raw_multiplier": raw_multiplier,
                "bounded_mult": bounded,
            },
        )
        next_state = ControllerState(
            entity_id=state.entity_id,
            date=state.date,
            pacing_multiplier=pacing_multiplier,
            throttle_prob=state.throttle_prob,
            shadow_lambda=state.shadow_lambda,
            last_update_ts_ms=snapshot.timestamp_ms,
            stale=False,
            integral_error=next_integral,
            debug=dict(state.debug),
        )
        return directive, next_state
