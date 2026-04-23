from ads_platform.ctr.calibrator import IdentityCalibrator
from ads_platform.ctr.predictor import OracleCTRPredictor
from ads_platform.decisioning.engine import DecisionEngine
from ads_platform.landscape.empirical import EmpiricalLandscapeModel, EmpiricalTable, SegmentCurve
from ads_platform.pacing.controllers import BoundedProportionalController
from ads_platform.pacing.desired_curve import UniformSpendCurve
from ads_platform.pacing.providers import InMemoryBudgetStateProvider
from ads_platform.pacing.state import ControllerState
from ads_platform.pacing.updater import BudgetTracker
from ads_platform.ranking.multislot import TopKAllocator
from ads_platform.ranking.scoring import ValueBasedRankScorer
from ads_platform.replay.historical_logs import record_from_json
from ads_platform.replay.budget_runner import BudgetReplayRunner
from ads_platform.schemas.pacing import PacingDirective


def test_budget_replay_runs_and_updates_controller():
    payload = {
        "request": {
            "request_id": "req_1",
            "timestamp_ms": 1_700_000_000_000,
            "device_type": "mobile",
            "country": "US",
            "placement": "feed",
            "app_or_site": "demo_app",
        },
        "candidates": [
            {
                "ad_id": "req_1_ad_1",
                "campaign_id": "global_budget",
                "adgroup_id": "ag_1",
                "base_bid": 1.5,
                "features": {},
                "extra": {"true_pctr": 0.2, "segment_id": 1},
            },
            {
                "ad_id": "req_1_ad_2",
                "campaign_id": "global_budget",
                "adgroup_id": "ag_2",
                "base_bid": 1.0,
                "features": {},
                "extra": {"true_pctr": 0.1, "segment_id": 1},
            },
        ],
        "outcomes": [
            {"clicked": 1, "price": 0.8, "true_pctr": 0.2},
            {"clicked": 0, "price": 0.3, "true_pctr": 0.1},
        ],
    }
    record = record_from_json(payload)
    predictor = OracleCTRPredictor(calibrator=IdentityCalibrator())
    provider = InMemoryBudgetStateProvider(states={}, default_directive=PacingDirective(pacing_multiplier=1.0, throttle_prob=1.0))
    landscape = EmpiricalLandscapeModel(
        tables_by_key={
            "channel:feed|global": EmpiricalTable(
                bids=[0.1, 1.0, 2.0],
                win_probs=[0.1, 0.5, 0.8],
                expected_costs=[0.05, 0.4, 0.9],
            ),
            "global": EmpiricalTable(
                bids=[0.1, 1.0, 2.0],
                win_probs=[0.1, 0.5, 0.8],
                expected_costs=[0.05, 0.4, 0.9],
            ),
        },
        default_curve=SegmentCurve(slope=1.0, midpoint=1.0, cost_fraction=0.6),
    )
    engine = DecisionEngine(
        predictor=predictor,
        landscape_model=landscape,
        budget_state_provider=provider,
        rank_scorer=ValueBasedRankScorer(),
        allocator=TopKAllocator(),
    )
    runner = BudgetReplayRunner(
        engine=engine,
        controller=BoundedProportionalController(kp=2.0),
        tracker=BudgetTracker(entity_id="global_budget", date="2026-04-07", budget_amount=10.0, desired_curve=UniformSpendCurve()),
    )
    per_auction = runner.run([record])
    assert len(per_auction) == 1
    assert runner.tracker.spend_so_far > 0.0
    assert len(runner.controller_updates) == 1


def test_budget_replay_respects_controller_update_interval():
    payload = {
        "request": {
            "request_id": "req_1",
            "timestamp_ms": 1_700_000_000_000,
            "device_type": "mobile",
            "country": "US",
            "placement": "feed",
            "app_or_site": "demo_app",
        },
        "candidates": [
            {
                "ad_id": "req_1_ad_1",
                "campaign_id": "global_budget",
                "adgroup_id": "ag_1",
                "base_bid": 1.5,
                "features": {},
                "extra": {"true_pctr": 0.2, "segment_id": 1},
            },
            {
                "ad_id": "req_1_ad_2",
                "campaign_id": "global_budget",
                "adgroup_id": "ag_2",
                "base_bid": 1.0,
                "features": {},
                "extra": {"true_pctr": 0.1, "segment_id": 1},
            },
        ],
        "outcomes": [
            {"clicked": 1, "price": 0.8, "true_pctr": 0.2},
            {"clicked": 0, "price": 0.3, "true_pctr": 0.1},
        ],
    }
    second_payload = {
        **payload,
        "request": {
            **payload["request"],
            "request_id": "req_2",
            "timestamp_ms": 1_700_000_000_100,  # 100ms later
        },
    }
    records = [record_from_json(payload), record_from_json(second_payload)]

    predictor = OracleCTRPredictor(calibrator=IdentityCalibrator())
    provider = InMemoryBudgetStateProvider(states={}, default_directive=PacingDirective(pacing_multiplier=1.0, throttle_prob=1.0))
    landscape = EmpiricalLandscapeModel(
        tables_by_key={
            "channel:feed|global": EmpiricalTable(
                bids=[0.1, 1.0, 2.0],
                win_probs=[0.1, 0.5, 0.8],
                expected_costs=[0.05, 0.4, 0.9],
            ),
            "global": EmpiricalTable(
                bids=[0.1, 1.0, 2.0],
                win_probs=[0.1, 0.5, 0.8],
                expected_costs=[0.05, 0.4, 0.9],
            ),
        },
        default_curve=SegmentCurve(slope=1.0, midpoint=1.0, cost_fraction=0.6),
    )
    engine = DecisionEngine(
        predictor=predictor,
        landscape_model=landscape,
        budget_state_provider=provider,
        rank_scorer=ValueBasedRankScorer(),
        allocator=TopKAllocator(),
    )
    runner = BudgetReplayRunner(
        engine=engine,
        controller=BoundedProportionalController(kp=2.0),
        tracker=BudgetTracker(entity_id="global_budget", date="2026-04-07", budget_amount=10.0, desired_curve=UniformSpendCurve()),
        controller_update_interval_ms=1000,
    )

    per_auction = runner.run(records)

    assert len(per_auction) == 2
    assert len(runner.controller_updates) == 1
