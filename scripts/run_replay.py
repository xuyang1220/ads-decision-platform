from __future__ import annotations

from ads_platform.ctr.bundle import CTRBundleLoader
from ads_platform.decisioning.engine import DecisionEngine
from ads_platform.landscape.empirical import EmpiricalLandscapeModel, SegmentCurve
from ads_platform.pacing.providers import InMemoryBudgetStateProvider
from ads_platform.ranking.multislot import TopKAllocator
from ads_platform.ranking.scoring import ValueBasedRankScorer
from ads_platform.replay.runner import ReplayRecord, ReplayRunner
from ads_platform.schemas.pacing import BudgetState, PacingDirective
from ads_platform.schemas.request import AdCandidate, AuctionInput, RequestContext


def build_demo_runner() -> ReplayRunner:
    bundle = CTRBundleLoader.load("artifacts/demo_bundle")
    landscape = EmpiricalLandscapeModel(
        curves_by_segment={1: SegmentCurve(slope=1.8, midpoint=1.0, cost_fraction=0.55)},
        default_curve=SegmentCurve(slope=1.2, midpoint=1.1, cost_fraction=0.60),
    )
    budget_provider = InMemoryBudgetStateProvider(
        states={
            "cmp_1": BudgetState(
                entity_id="cmp_1",
                date="2026-04-02",
                budget_amount=100.0,
                spend_so_far=15.0,
                target_spend_so_far=20.0,
                pacing_multiplier=1.1,
                throttle_prob=1.0,
                shadow_lambda=0.9,
                last_update_ts_ms=0,
                stale=False,
            )
        },
        default_directive=PacingDirective(pacing_multiplier=1.0, throttle_prob=1.0),
    )
    engine = DecisionEngine(
        predictor=bundle.predictor,
        landscape_model=landscape,
        budget_state_provider=budget_provider,
        rank_scorer=ValueBasedRankScorer(use_landscape_in_score=True),
        allocator=TopKAllocator(),
    )
    return ReplayRunner(engine)


def main() -> None:
    runner = build_demo_runner()
    records = [
        ReplayRecord(
            auction_input=AuctionInput(
                request=RequestContext(
                    request_id="req_demo_1",
                    timestamp_ms=1,
                    user_id="u1",
                    device_type="mobile",
                    country="US",
                    placement="feed",
                    app_or_site="demo_app",
                ),
                candidates=[
                    AdCandidate(ad_id="ad_1", campaign_id="cmp_1", adgroup_id="ag_1", base_bid=1.2, features={"historical_ctr": 0.02}, extra={"segment_id": 1}),
                    AdCandidate(ad_id="ad_2", campaign_id="cmp_2", adgroup_id="ag_2", base_bid=0.9, features={"historical_ctr": 0.04}, extra={"segment_id": 2}),
                ],
            ),
            num_slots=1,
            observed_clicked_ad_ids=["ad_1"],
            observed_spend_by_ad_id={"ad_1": 0.62},
        )
    ]
    summary, per_auction = runner.run(records)
    print(summary)
    print(per_auction[0]["selected_ad_ids"])


if __name__ == "__main__":
    main()
