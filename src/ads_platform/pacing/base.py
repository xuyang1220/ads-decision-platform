from __future__ import annotations

from abc import ABC, abstractmethod

from ads_platform.schemas.pacing import BudgetState, PacingDirective


class BudgetController(ABC):
    @abstractmethod
    def update(self, state: BudgetState) -> PacingDirective:
        raise NotImplementedError


class BudgetStateProvider(ABC):
    @abstractmethod
    def get_state(self, entity_id: str) -> BudgetState:
        raise NotImplementedError
