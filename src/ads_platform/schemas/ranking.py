from typing import Optional, List
from request import AdCandidate
from prediction import PredictionResult
from pacing import PacingDirective, LandscapeEstimate
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class ScoredCandidate:
    candidate: AdCandidate
    prediction: PredictionResult
    bid: float
    throttle_prob: float
    rank_score: float
    landscape: Optional[LandscapeEstimate] = None
    debug: dict | None = None


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
    

class ValueBasedRankScorer(RankScorer):
    def score(
        self,
        candidate: AdCandidate,
        prediction: PredictionResult,
        directive: PacingDirective,
        landscape: LandscapeEstimate | None,
    ) -> ScoredCandidate:
        effective_bid = candidate.base_bid * directive.pacing_multiplier
        rank_score = prediction.pctr_calibrated * effective_bid
        return ScoredCandidate(
            candidate=candidate,
            prediction=prediction,
            bid=effective_bid,
            throttle_prob=directive.throttle_prob,
            rank_score=rank_score,
            landscape=landscape,
            debug={"formula": "pctr_calibrated * effective_bid"},
        )
    

@dataclass
class AuctionResult:
    request_id: str
    winners: List[ScoredCandidate]
    dropped: List[ScoredCandidate]
    debug: dict | None = None


class MultiSlotAllocator(ABC):
    @abstractmethod
    def allocate(
        self,
        scored_candidates: List[ScoredCandidate],
        num_slots: int,
    ) -> AuctionResult:
        raise NotImplementedError