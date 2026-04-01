from typing import Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class BudgetState:
    entity_id: str
    date: str
    budget_amount: float
    spend_so_far: float
    target_spend_so_far: float
    pacing_multiplier: float
    throttle_prob: float
    shadow_lambda: Optional[float]
    last_update_ts_ms: int
    stale: bool = False
    debug: dict | None = None

@dataclass
class PacingDirective:
    pacing_multiplier: float
    throttle_prob: float
    shadow_lambda: Optional[float] = None
    reason: str = ""
    debug: dict | None = None

class BudgetController(ABC):
    @abstractmethod
    def update(self, state: BudgetState) -> PacingDirective:
        raise NotImplementedError

class BoundedProportionalController(BudgetController):
    def __init__(
        self,
        kp: float,
        min_multiplier: float = 0.5,
        max_multiplier: float = 1.5,
    ):
        self.kp = kp
        self.min_multiplier = min_multiplier
        self.max_multiplier = max_multiplier

    def update(self, state: BudgetState) -> PacingDirective:
        error = state.target_spend_so_far - state.spend_so_far
        raw_mult = state.pacing_multiplier * (1.0 + self.kp * error / max(state.budget_amount, 1e-9))
        mult = min(self.max_multiplier, max(self.min_multiplier, raw_mult))
        return PacingDirective(
            pacing_multiplier=mult,
            throttle_prob=1.0,
            shadow_lambda=state.shadow_lambda,
            reason="bounded_proportional_update",
            debug={"error": error, "raw_mult": raw_mult},
        )