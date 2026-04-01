from ads_platform.ctr.calibrator import IdentityCalibrator
from ads_platform.ctr.predictor import DeepFMPredictor, DictFeatureTransformer, DummyCTRModel
from ads_platform.decisioning.engine import DecisionEngine
from ads_platform.landscape.empirical import EmpiricalLandscapeModel, SegmentCurve
from ads_platform.pacing.providers import InMemoryBudgetStateProvider
from ads_platform.ranking.multislot import TopKAllocator
from ads_platform.ranking.scoring import ValueBasedRankScorer
from ads_platform.schemas.pacing import BudgetState, PacingDirective
from ads_platform.schemas.request import AdCandidate, AuctionInput, RequestContext


def test_decision_engine_end_to_end() -> None:
    predictor = DeepFMPredictor(
        model=DummyCTRModel(),
        transformer=DictFeatureTransformer(),
        calibrator=IdentityCalibrator(),
        model_version="deepfm_test",
        calibration_version="identity_test",
    )
    landscape = EmpiricalLandscapeModel(
        curves_by_segment={1: SegmentCurve(slope=2.0, midpoint=1.0, cost_fraction=0.7)},
        default_curve=SegmentCurve(slope=1.2, midpoint=0.9, cost_fraction=0.65),
        model_version="empirical_test",
    )
    budget_provider = InMemoryBudgetStateProvider(
        states={
            "cmp_1": BudgetState(
                entity_id="cmp_1",
                date="2026-04-01",
                budget_amount=100.0,
                spend_so_far=20.0,
                target_spend_so_far=25.0,
                pacing_multiplier=1.1,
                throttle_prob=1.0,
                shadow_lambda=0.8,
                last_update_ts_ms=1,
                stale=False,
            ),
            "cmp_2": BudgetState(
                entity_id="cmp_2",
                date="2026-04-01",
                budget_amount=100.0,
                spend_so_far=35.0,
                target_spend_so_far=30.0,
                pacing_multiplier=0.9,
                throttle_prob=1.0,
                shadow_lambda=1.1,
                last_update_ts_ms=1,
                stale=False,
            ),
        },
        default_directive=PacingDirective(pacing_multiplier=1.0, throttle_prob=1.0),
    )
    engine = DecisionEngine(
        predictor=predictor,
        landscape_model=landscape,
        budget_state_provider=budget_provider,
        rank_scorer=ValueBasedRankScorer(use_landscape_in_score=True),
        allocator=TopKAllocator(),
    )

    auction_input = AuctionInput(
        request=RequestContext(
            request_id="req_123",
            timestamp_ms=1_712_000_000_000,
            user_id="u1",
            device_type="mobile",
            country="NL",
            placement="feed",
            app_or_site="example_app",
        ),
        candidates=[
            AdCandidate(
                ad_id="ad_a",
                campaign_id="cmp_1",
                adgroup_id="ag_1",
                advertiser_id="adv_1",
                base_bid=1.4,
                features={"historical_ctr": 0.03},
                extra={"segment_id": 1},
            ),
            AdCandidate(
                ad_id="ad_b",
                campaign_id="cmp_2",
                adgroup_id="ag_2",
                advertiser_id="adv_2",
                base_bid=1.8,
                features={"historical_ctr": 0.02},
                extra={"segment_id": 2},
            ),
            AdCandidate(
                ad_id="ad_c",
                campaign_id="cmp_1",
                adgroup_id="ag_3",
                advertiser_id="adv_3",
                base_bid=1.0,
                features={"historical_ctr": 0.01},
                extra={"segment_id": 1},
            ),
        ],
    )

    result = engine.decide(auction_input=auction_input, num_slots=2)

    assert result.request_id == "req_123"
    assert len(result.winners) == 2
    assert len(result.dropped) == 1
    assert result.winners[0].rank_score >= result.winners[1].rank_score

    logs = engine.build_decision_logs(auction_input=auction_input, result=result)
    assert len(logs) == 3
    assert sum(log.selected for log in logs) == 2
    assert all(0.0 <= log.pctr_calibrated <= 1.0 for log in logs)
