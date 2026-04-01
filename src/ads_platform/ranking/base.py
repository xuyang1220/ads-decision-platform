from __future__ import annotations

from abc import ABC, abstractmethod

from ads_platform.schemas.landscape import LandscapeEstimate
from ads_platform.schemas.pacing import PacingDirective
from ads_platform.schemas.prediction import PredictionResult
from ads_platform.schemas.ranking import AuctionResult, ScoredCandidate
from ads_platform.schemas.request import AdCandidate


class RankScorer(ABC):
    @abstractmethod
    def score(
        self,
        candidate: AdCandidate,
        prediction: PredictionResult,
        directive: PacingDirective,
        landscape: LandscapeEstimate | None,
    ) -> ScoredCandidate:
        raise NotImplementedError


class MultiSlotAllocator(ABC):
    @abstractmethod
    def allocate(
        self,
        request_id: str,
        scored_candidates: list[ScoredCandidate],
        num_slots: int,
    ) -> AuctionResult:
        raise NotImplementedError
