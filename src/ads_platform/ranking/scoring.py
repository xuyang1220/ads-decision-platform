from __future__ import annotations

from ads_platform.ranking.base import RankScorer
from ads_platform.schemas.landscape import LandscapeEstimate
from ads_platform.schemas.pacing import PacingDirective
from ads_platform.schemas.prediction import PredictionResult
from ads_platform.schemas.ranking import ScoredCandidate
from ads_platform.schemas.request import AdCandidate


class ValueBasedRankScorer(RankScorer):
    def __init__(self, use_landscape_in_score: bool = False):
        self.use_landscape_in_score = use_landscape_in_score

    def score(
        self,
        candidate: AdCandidate,
        prediction: PredictionResult,
        directive: PacingDirective,
        landscape: LandscapeEstimate | None,
    ) -> ScoredCandidate:
        effective_bid = candidate.base_bid * directive.pacing_multiplier
        rank_score = prediction.pctr_calibrated * effective_bid
        formula = "pctr_calibrated * effective_bid"

        if self.use_landscape_in_score and landscape is not None:
            rank_score *= landscape.win_prob
            formula += " * estimated_win_prob"

        return ScoredCandidate(
            candidate=candidate,
            prediction=prediction,
            bid=effective_bid,
            throttle_prob=directive.throttle_prob,
            rank_score=rank_score,
            landscape=landscape,
            debug={"formula": formula, "shadow_lambda": directive.shadow_lambda},
        )
