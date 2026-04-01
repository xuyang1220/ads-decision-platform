from __future__ import annotations

from ads_platform.common.utils import clip
from ads_platform.pacing.base import BudgetController
from ads_platform.schemas.pacing import BudgetState, PacingDirective


class BoundedProportionalController(BudgetController):
    def __init__(
        self,
        kp: float,
        min_multiplier: float = 0.5,
        max_multiplier: float = 1.5,
        stale_throttle_prob: float = 0.5,
    ):
        self.kp = kp
        self.min_multiplier = min_multiplier
        self.max_multiplier = max_multiplier
        self.stale_throttle_prob = stale_throttle_prob

    def update(self, state: BudgetState) -> PacingDirective:
        if state.stale:
            return PacingDirective(
                pacing_multiplier=min(state.pacing_multiplier, 1.0),
                throttle_prob=self.stale_throttle_prob,
                shadow_lambda=state.shadow_lambda,
                reason="stale_state_safe_mode",
                debug={"entity_id": state.entity_id},
            )

        budget_denom = max(state.budget_amount, 1e-9)
        error = state.target_spend_so_far - state.spend_so_far
        raw_mult = state.pacing_multiplier * (1.0 + self.kp * error / budget_denom)
        mult = clip(raw_mult, self.min_multiplier, self.max_multiplier)
        return PacingDirective(
            pacing_multiplier=mult,
            throttle_prob=state.throttle_prob,
            shadow_lambda=state.shadow_lambda,
            reason="bounded_proportional_update",
            debug={"entity_id": state.entity_id, "error": error, "raw_mult": raw_mult},
        )
