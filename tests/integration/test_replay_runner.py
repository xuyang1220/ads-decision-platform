from ads_platform.ctr.bundle import CTRBundleLoader
from ads_platform.decisioning.engine import DecisionEngine
from ads_platform.landscape.empirical import EmpiricalLandscapeModel, SegmentCurve
from ads_platform.pacing.providers import InMemoryBudgetStateProvider
from ads_platform.ranking.multislot import TopKAllocator
from ads_platform.ranking.scoring import ValueBasedRankScorer
from ads_platform.replay.runner import ReplayRecord, ReplayRunner
from ads_platform.schemas.pacing import BudgetState, PacingDirective
from ads_platform.schemas.request import AdCandidate, AuctionInput, RequestContext


def test_replay_runner_end_to_end() -> None:
    bundle = CTRBundleLoader.load("artifacts/demo_bundle")
    engine = DecisionEngine(
        predictor=bundle.predictor,
        landscape_model=EmpiricalLandscapeModel(
            curves_by_segment={1: SegmentCurve(slope=2.0, midpoint=1.1, cost_fraction=0.5)},
            default_curve=SegmentCurve(slope=1.5, midpoint=1.0, cost_fraction=0.6),
        ),
        budget_state_provider=InMemoryBudgetStateProvider(
            states={
                "cmp_1": BudgetState(
                    entity_id="cmp_1",
                    date="2026-04-02",
                    budget_amount=100.0,
                    spend_so_far=20.0,
                    target_spend_so_far=20.0,
                    pacing_multiplier=1.0,
                    throttle_prob=1.0,
                    shadow_lambda=1.0,
                    last_update_ts_ms=1,
                    stale=False,
                )
            },
            default_directive=PacingDirective(pacing_multiplier=1.0, throttle_prob=1.0),
        ),
        rank_scorer=ValueBasedRankScorer(use_landscape_in_score=True),
        allocator=TopKAllocator(),
    )
    runner = ReplayRunner(engine)
    records = [
        ReplayRecord(
            auction_input=AuctionInput(
                request=RequestContext(
                    request_id="req_1",
                    timestamp_ms=1,
                    user_id="u1",
                    device_type="mobile",
                    country="US",
                    placement="feed",
                    app_or_site="app",
                ),
                candidates=[
                    AdCandidate(ad_id="ad_1", campaign_id="cmp_1", adgroup_id="ag_1", base_bid=1.1, features={"historical_ctr": 0.03}, extra={"segment_id": 1}),
                    AdCandidate(ad_id="ad_2", campaign_id="cmp_2", adgroup_id="ag_2", base_bid=0.8, features={"historical_ctr": 0.02}, extra={"segment_id": 2}),
                ],
            ),
            num_slots=1,
            observed_clicked_ad_ids=["ad_1"],
            observed_spend_by_ad_id={"ad_1": 0.55},
        )
    ]
    summary, per_auction = runner.run(records)
    assert summary.num_auctions == 1
    assert summary.num_candidates == 2
    assert summary.num_winners == 1
    assert per_auction[0]["request_id"] == "req_1"
    assert len(per_auction[0]["decision_logs"]) == 2
