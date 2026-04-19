from __future__ import annotations

import argparse
import json

from ads_platform.common.serialization import to_dict
from ads_platform.ctr.bundle import CTRBundleLoader
from ads_platform.ctr.calibrator import IdentityCalibrator
from ads_platform.ctr.predictor import NoisyOracleCTRPredictor, OracleCTRPredictor
from ads_platform.decisioning.engine import DecisionEngine
from ads_platform.evaluation.pacing_diagnostics import build_pacing_summary
from ads_platform.evaluation.replay_diagnostics import build_calibration_table, build_predicted_vs_observed
from ads_platform.evaluation.spend_diagnostics import build_spend_summary
from ads_platform.evaluation.spend_diagnostics import build_spend_by_bid_bucket
from ads_platform.landscape.empirical import EmpiricalLandscapeModel, EmpiricalTable, SegmentCurve
from ads_platform.landscape.loader import load_empirical_landscape
from ads_platform.pacing.controllers import BoundedProportionalController
from ads_platform.pacing.desired_curve import FrontLoadedSpendCurve, UniformSpendCurve
from ads_platform.pacing.providers import InMemoryBudgetStateProvider
from ads_platform.pacing.state import ControllerState
from ads_platform.pacing.updater import BudgetTracker
from ads_platform.ranking.multislot import TopKAllocator
from ads_platform.ranking.scoring import ValueBasedRankScorer
from ads_platform.replay.historical_logs import load_historical_replay_records
from ads_platform.replay.runner import ReplayRunner
from ads_platform.replay.budget_runner import BudgetReplayRunner
from ads_platform.schemas.landscape import LandscapeContext
from ads_platform.schemas.pacing import BudgetState, PacingDirective




def build_predictor(args):
    if args.predictor_mode == "bundle":
        if not args.bundle_dir:
            raise ValueError("--bundle-dir is required when using bundle predictor mode")
        return CTRBundleLoader.load(args.bundle_dir, device=args.device).predictor
    if args.predictor_mode == "oracle":
        return OracleCTRPredictor(calibrator=IdentityCalibrator())
    if args.predictor_mode == "noisy_oracle":
        return NoisyOracleCTRPredictor(calibrator=IdentityCalibrator(), noise_sigma=args.noise_sigma, bias=args.noise_bias)
    raise ValueError(f"Unsupported predictor mode: {args.predictor_mode}")


def build_curve(name: str):
    if name == "uniform":
        return UniformSpendCurve()
    if name == "frontloaded":
        return FrontLoadedSpendCurve()
    raise ValueError(name)


def build_landscape(landscape_artifact: str | None = None) -> EmpiricalLandscapeModel:
    if landscape_artifact:
        return load_empirical_landscape(landscape_artifact)
    return EmpiricalLandscapeModel(
        tables_by_key={
            "channel:feed|global": EmpiricalTable(
                bids=[0.1, 0.5, 1.0, 1.5, 2.0, 3.0],
                win_probs=[0.05, 0.15, 0.32, 0.48, 0.62, 0.8],
                expected_costs=[0.03, 0.12, 0.28, 0.46, 0.66, 1.05],
            ),
            "global": EmpiricalTable(
                bids=[0.1, 0.5, 1.0, 1.5, 2.0, 3.0],
                win_probs=[0.04, 0.12, 0.25, 0.40, 0.55, 0.75],
                expected_costs=[0.02, 0.10, 0.22, 0.38, 0.56, 0.94],
            ),
        },
        curves_by_segment={None: SegmentCurve(slope=1.2, midpoint=1.0, cost_fraction=0.7)},
        default_curve=SegmentCurve(slope=1.2, midpoint=1.0, cost_fraction=0.7),
        model_version="budget_replay_empirical_v1",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay historical logs with a budget controller")
    parser.add_argument("--logs-path", required=True)
    parser.add_argument("--bundle-dir")
    parser.add_argument("--predictor-mode", choices=["bundle", "oracle", "noisy_oracle"], default="oracle")
    parser.add_argument("--noise-sigma", type=float, default=0.5)
    parser.add_argument("--noise-bias", type=float, default=0.0)
    parser.add_argument("--budget", type=float, required=True)
    parser.add_argument("--curve", choices=["uniform", "frontloaded"], default="uniform")
    parser.add_argument("--kp", type=float, default=2.0)
    parser.add_argument("--entity-id", default="global_budget")
    parser.add_argument("--date", default="1970-01-01")
    parser.add_argument("--default-num-slots", type=int, default=1)
    parser.add_argument("--num-buckets", type=int, default=10)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--landscape-artifact")
    args = parser.parse_args()

    records = load_historical_replay_records(args.logs_path, default_num_slots=args.default_num_slots)
    predictor = build_predictor(args)
    default_directive = PacingDirective(pacing_multiplier=1.0, throttle_prob=1.0, reason="budget_replay_default")
    budget_provider = InMemoryBudgetStateProvider(states={}, default_directive=default_directive)
    engine = DecisionEngine(
        predictor=predictor,
        landscape_model=build_landscape(args.landscape_artifact),
        budget_state_provider=budget_provider,
        rank_scorer=ValueBasedRankScorer(use_landscape_in_score=False),
        allocator=TopKAllocator(),
    )
    controller = BoundedProportionalController(kp=args.kp)
    tracker = BudgetTracker(entity_id=args.entity_id, date=args.date, budget_amount=args.budget, desired_curve=build_curve(args.curve))
    runner = BudgetReplayRunner(engine=engine, controller=controller, tracker=tracker)
    per_auction = runner.run(records)
    baseline_summary = ReplayRunner(engine).run(records)[0]
    bid_bucket_table = build_spend_by_bid_bucket(per_auction, num_buckets=5)

    output = {
        "mode": args.predictor_mode,
        "budget_summary": build_spend_summary(per_auction, budget_amount=args.budget),
        "spend_by_bid_bucket": bid_bucket_table,
        "controller_summary": build_pacing_summary(runner.controller_updates),
        "predicted_vs_observed_clicks": build_predicted_vs_observed(baseline_summary),
        "calibration_table": [to_dict(row) for row in build_calibration_table(per_auction, num_buckets=args.num_buckets)],
        "num_auction_details": len(per_auction),
    }
    print(json.dumps(to_dict(output), indent=2))


if __name__ == "__main__":
    main()
