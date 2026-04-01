from __future__ import annotations

from ads_platform.common.exceptions import MissingBudgetStateError
from ads_platform.pacing.base import BudgetStateProvider
from ads_platform.schemas.pacing import BudgetState, PacingDirective


class InMemoryBudgetStateProvider(BudgetStateProvider):
    def __init__(self, states: dict[str, BudgetState], default_directive: PacingDirective | None = None):
        self.states = states
        self.default_directive = default_directive

    def get_state(self, entity_id: str) -> BudgetState:
        if entity_id in self.states:
            return self.states[entity_id]
        if self.default_directive is not None:
            return BudgetState(
                entity_id=entity_id,
                date="1970-01-01",
                budget_amount=1.0,
                spend_so_far=0.0,
                target_spend_so_far=0.0,
                pacing_multiplier=self.default_directive.pacing_multiplier,
                throttle_prob=self.default_directive.throttle_prob,
                shadow_lambda=self.default_directive.shadow_lambda,
                last_update_ts_ms=0,
                stale=True,
                debug={"fallback": True},
            )
        raise MissingBudgetStateError(f"Missing budget state for entity_id={entity_id}")
