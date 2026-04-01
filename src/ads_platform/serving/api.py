from __future__ import annotations

from fastapi import FastAPI

from ads_platform.ctr.calibrator import IdentityCalibrator
from ads_platform.ctr.predictor import DeepFMPredictor, DictFeatureTransformer, DummyCTRModel
from ads_platform.decisioning.engine import DecisionEngine
from ads_platform.landscape.empirical import EmpiricalLandscapeModel, SegmentCurve
from ads_platform.pacing.providers import InMemoryBudgetStateProvider
from ads_platform.ranking.multislot import TopKAllocator
from ads_platform.ranking.scoring import ValueBasedRankScorer
from ads_platform.schemas.pacing import BudgetState, PacingDirective
from ads_platform.schemas.request import AuctionInput


def build_app() -> FastAPI:
    predictor = DeepFMPredictor(
        model=DummyCTRModel(),
        transformer=DictFeatureTransformer(),
        calibrator=IdentityCalibrator(),
    )
    landscape = EmpiricalLandscapeModel(
        curves_by_segment={1: SegmentCurve(slope=2.0, midpoint=1.2, cost_fraction=0.7)},
        default_curve=SegmentCurve(slope=1.5, midpoint=1.0, cost_fraction=0.65),
    )
    budget_provider = InMemoryBudgetStateProvider(
        states={},
        default_directive=PacingDirective(pacing_multiplier=1.0, throttle_prob=1.0),
    )
    # Example hard-coded state for local testing.
    budget_provider.states["cmp_demo"] = BudgetState(
        entity_id="cmp_demo",
        date="2026-04-01",
        budget_amount=1000.0,
        spend_so_far=200.0,
        target_spend_so_far=250.0,
        pacing_multiplier=1.1,
        throttle_prob=1.0,
        shadow_lambda=0.9,
        last_update_ts_ms=0,
        stale=False,
    )
    engine = DecisionEngine(
        predictor=predictor,
        landscape_model=landscape,
        budget_state_provider=budget_provider,
        rank_scorer=ValueBasedRankScorer(use_landscape_in_score=True),
        allocator=TopKAllocator(),
    )

    app = FastAPI(title="ads_decision_platform")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/decide")
    def decide(auction_input: AuctionInput, num_slots: int = 4) -> dict:
        result = engine.decide(auction_input=auction_input, num_slots=num_slots)
        logs = engine.build_decision_logs(auction_input=auction_input, result=result)
        return {
            "auction_result": result.model_dump(mode="json"),
            "decision_logs": [row.model_dump(mode="json") for row in logs],
        }

    return app


app = build_app()
