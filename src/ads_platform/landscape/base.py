from __future__ import annotations

from abc import ABC, abstractmethod

from ads_platform.schemas.landscape import LandscapeContext, LandscapeEstimate


class BidLandscapeModel(ABC):
    @abstractmethod
    def estimate(self, bid: float, context: LandscapeContext) -> LandscapeEstimate:
        raise NotImplementedError

    def win_prob(self, bid: float, context: LandscapeContext) -> float:
        return self.estimate(bid=bid, context=context).win_prob

    def expected_cost(self, bid: float, context: LandscapeContext) -> float:
        return self.estimate(bid=bid, context=context).expected_cost

    def expected_spend(self, bid: float, context: LandscapeContext) -> float:
        estimate = self.estimate(bid=bid, context=context)
        return estimate.win_prob * estimate.expected_cost

    @abstractmethod
    def optimal_bid(
        self,
        context: LandscapeContext,
        value_per_click: float,
        bid_cap: float | None = None,
    ) -> float:
        raise NotImplementedError
