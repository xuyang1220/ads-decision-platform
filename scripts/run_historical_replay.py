from __future__ import annotations

import argparse
import json

from ads_platform.common.serialization import to_dict
from ads_platform.ctr.bundle import CTRBundleLoader
from ads_platform.ctr.calibrator import IdentityCalibrator
from ads_platform.ctr.predictor import NoisyOracleCTRPredictor, OracleCTRPredictor
from ads_platform.decisioning.engine import DecisionEngine
from ads_platform.evaluation.replay_diagnostics import (
    build_calibration_table,
    build_policy_row,
    build_predicted_vs_observed,
)
from ads_platform.landscape.empirical import EmpiricalLandscapeModel, SegmentCurve
from ads_platform.pacing.providers import InMemoryBudgetStateProvider
from ads_platform.ranking.multislot import TopKAllocator
from ads_platform.ranking.scoring import ValueBasedRankScorer
from ads_platform.replay.historical_logs import load_historical_replay_records
from ads_platform.replay.runner import ReplayRunner
from ads_platform.schemas.pacing import PacingDirective


def build_predictor(args: argparse.Namespace, mode: str):
    if mode == "bundle":
        if not args.bundle_dir:
            raise ValueError("--bundle-dir is required when using bundle predictor mode")
        return CTRBundleLoader.load(args.bundle_dir, device=args.device).predictor
    if mode == "oracle":
        return OracleCTRPredictor(calibrator=IdentityCalibrator())
    if mode == "noisy_oracle":
        return NoisyOracleCTRPredictor(
            calibrator=IdentityCalibrator(),
            noise_sigma=args.noise_sigma,
            bias=args.noise_bias,
        )
    raise ValueError(f"Unsupported predictor mode: {mode}")


def build_engine(args: argparse.Namespace, mode: str) -> DecisionEngine:
    predictor = build_predictor(args, mode)
    default_directive = PacingDirective(
        pacing_multiplier=1.0,
        throttle_prob=1.0,
        shadow_lambda=None,
        reason="replay_default",
    )
    budget_provider = InMemoryBudgetStateProvider(states={}, default_directive=default_directive)
    landscape_model = EmpiricalLandscapeModel(
        curves_by_segment={None: SegmentCurve(slope=1.2, midpoint=1.0, cost_fraction=0.7)},
        default_curve=SegmentCurve(slope=1.2, midpoint=1.0, cost_fraction=0.7),
        model_version="replay_empirical_v1",
    )
    return DecisionEngine(
        predictor=predictor,
        landscape_model=landscape_model,
        budget_state_provider=budget_provider,
        rank_scorer=ValueBasedRankScorer(use_landscape_in_score=False),
        allocator=TopKAllocator(),
    )


def run_mode(args: argparse.Namespace, mode: str, records):
    engine = build_engine(args, mode)
    summary, per_auction = ReplayRunner(engine).run(records)
    calibration_table = build_calibration_table(per_auction, num_buckets=args.num_buckets)

    assert abs(
        sum(b.predicted_clicks for b in calibration_table)
        - summary.predicted_clicks
    ) < 1e-6
    assert sum(b.observed_clicks for b in calibration_table) == summary.observed_clicks_on_selected

    return {
        'mode': mode,
        'summary': to_dict(summary),
        'predicted_vs_observed_clicks': build_predicted_vs_observed(summary),
        'calibration_table': [to_dict(row) for row in calibration_table],
        'num_auction_details': len(per_auction),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay historical auction logs against one or more predictors")
    parser.add_argument("--bundle-dir")
    parser.add_argument("--predictor-mode", choices=["bundle", "oracle", "noisy_oracle"], default="bundle")
    parser.add_argument("--compare-modes", nargs="+", choices=["oracle", "noisy_oracle", "bundle"])
    parser.add_argument("--noise-sigma", type=float, default=0.5)
    parser.add_argument("--noise-bias", type=float, default=0.0)
    parser.add_argument("--logs-path", required=True, help="JSONL file with one auction record per line")
    parser.add_argument("--default-num-slots", type=int, default=1)
    parser.add_argument("--num-buckets", type=int, default=10)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    records = load_historical_replay_records(args.logs_path, default_num_slots=args.default_num_slots)
    modes = args.compare_modes or [args.predictor_mode]

    runs = [run_mode(args, mode, records) for mode in modes]
    output = runs[0] if len(runs) == 1 else {
        'runs': runs,
        'policy_comparison_summary': [build_policy_row(run['mode'], type('Summary', (), run['summary'])()) for run in runs],
    }
    print(json.dumps(to_dict(output), indent=2))


if __name__ == "__main__":
    main()
