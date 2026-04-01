from __future__ import annotations

from ads_platform.ctr.base import CTRPredictor
from ads_platform.landscape.base import BidLandscapeModel
from ads_platform.pacing.base import BudgetStateProvider
from ads_platform.ranking.base import MultiSlotAllocator, RankScorer
from ads_platform.schemas.landscape import LandscapeContext
from ads_platform.schemas.logs import DecisionLog
from ads_platform.schemas.ranking import AuctionResult
from ads_platform.schemas.request import AuctionInput


class DecisionEngine:
    def __init__(
        self,
        predictor: CTRPredictor,
        landscape_model: BidLandscapeModel,
        budget_state_provider: BudgetStateProvider,
        rank_scorer: RankScorer,
        allocator: MultiSlotAllocator,
    ):
        self.predictor = predictor
        self.landscape_model = landscape_model
        self.budget_state_provider = budget_state_provider
        self.rank_scorer = rank_scorer
        self.allocator = allocator

    def decide(self, auction_input: AuctionInput, num_slots: int) -> AuctionResult:
        scored = []
        for candidate in auction_input.candidates:
            pred = self.predictor.predict(auction_input.request, candidate)
            budget_state = self.budget_state_provider.get_state(candidate.campaign_id)
            directive = budget_state.current_directive

            landscape_context = LandscapeContext(
                campaign_id=candidate.campaign_id,
                adgroup_id=candidate.adgroup_id,
                segment_id=candidate.extra.get("segment_id"),
                channel=auction_input.request.placement,
                extra={"country": auction_input.request.country},
            )
            landscape = self.landscape_model.estimate(
                bid=candidate.base_bid * directive.pacing_multiplier,
                context=landscape_context,
            )
            scored_candidate = self.rank_scorer.score(
                candidate=candidate,
                prediction=pred,
                directive=directive,
                landscape=landscape,
            )
            scored.append(scored_candidate)

        return self.allocator.allocate(
            request_id=auction_input.request.request_id,
            scored_candidates=scored,
            num_slots=num_slots,
        )

    @staticmethod
    def build_decision_logs(auction_input: AuctionInput, result: AuctionResult) -> list[DecisionLog]:
        winners_by_ad_id = {winner.candidate.ad_id: idx for idx, winner in enumerate(result.winners)}
        rows = []
        for scored in [*result.winners, *result.dropped]:
            slot = winners_by_ad_id.get(scored.candidate.ad_id)
            rows.append(
                DecisionLog(
                    request_id=auction_input.request.request_id,
                    ad_id=scored.candidate.ad_id,
                    campaign_id=scored.candidate.campaign_id,
                    model_version=scored.prediction.model_version,
                    calibration_version=scored.prediction.calibration_version,
                    landscape_version=scored.landscape.model_version if scored.landscape else "",
                    pctr_raw=scored.prediction.pctr_raw,
                    pctr_calibrated=scored.prediction.pctr_calibrated,
                    bid_base=scored.candidate.base_bid,
                    bid_effective=scored.bid,
                    throttle_prob=scored.throttle_prob,
                    pacing_multiplier=scored.bid / scored.candidate.base_bid if scored.candidate.base_bid > 0 else 0.0,
                    shadow_lambda=scored.debug.get("shadow_lambda"),
                    estimated_win_prob=scored.landscape.win_prob if scored.landscape else None,
                    estimated_cost=scored.landscape.expected_cost if scored.landscape else None,
                    rank_score=scored.rank_score,
                    selected=slot is not None,
                    slot=slot,
                    timestamp_ms=auction_input.request.timestamp_ms,
                    debug=scored.debug,
                )
            )
        return rows
