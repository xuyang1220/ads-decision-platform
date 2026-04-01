from __future__ import annotations

from abc import ABC, abstractmethod

from ads_platform.schemas.landscape import LandscapeContext, LandscapeEstimate


class BidLandscapeModel(ABC):
    @abstractmethod
    def estimate(self, bid: float, context: LandscapeContext) -> LandscapeEstimate:
        raise NotImplementedError

    @abstractmethod
    def optimal_bid(
        self,
        context: LandscapeContext,
        value_per_click: float,
        bid_cap: float | None = None,
    ) -> float:
        raise NotImplementedError
