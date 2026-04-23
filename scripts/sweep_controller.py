from __future__ import annotations

import argparse
import itertools
import json
from typing import Any

from ads_platform.common.serialization import to_dict
from ads_platform.ctr.bundle import CTRBundleLoader
from ads_platform.ctr.calibrator import IdentityCalibrator
from ads_platform.ctr.predictor import NoisyOracleCTRPredictor, OracleCTRPredictor
from ads_platform.decisioning.engine import DecisionEngine
from ads_platform.evaluation.pacing_diagnostics import build_pacing_summary
from ads_platform.evaluation.spend_diagnostics import build_spend_summary
from ads_platform.evaluation.time_pacing_diagnostics import build_time_bucketed_pacing_diagnostics
from ads_platform.landscape.empirical import EmpiricalLandscapeModel, EmpiricalTable, SegmentCurve
from ads_platform.landscape.loader import load_empirical_landscape
from ads_platform.pacing.controllers import BoundedProportionalController
from ads_platform.pacing.desired_curve import FrontLoadedSpendCurve, UniformSpendCurve
from ads_platform.pacing.providers import InMemoryBudgetStateProvider
from ads_platform.pacing.updater import BudgetTracker
from ads_platform.ranking.multislot import TopKAllocator
from ads_platform.ranking.scoring import ValueBasedRankScorer
from ads_platform.replay.budget_runner import BudgetReplayRunner
from ads_platform.replay.historical_logs import load_historical_replay_records
from ads_platform.schemas.pacing import PacingDirective


def build_predictor(args: argparse.Namespace):
    if args.predictor_mode == "bundle":
        if not args.bundle_dir:
            raise ValueError("--bundle-dir is required when using bundle predictor mode")
        return CTRBundleLoader.load(args.bundle_dir, device=args.device).predictor
    if args.predictor_mode == "oracle":
        return OracleCTRPredictor(calibrator=IdentityCalibrator())
    if args.predictor_mode == "noisy_oracle":
        return NoisyOracleCTRPredictor(
            calibrator=IdentityCalibrator(),
            noise_sigma=args.noise_sigma,
            bias=args.noise_bias,
        )
    raise ValueError(f"Unsupported predictor mode: {args.predictor_mode}")


def build_curve(name: str):
    if name == "uniform":
        return UniformSpendCurve()
    if name == "frontloaded":
        return FrontLoadedSpendCurve()
    raise ValueError(f"Unsupported curve: {name}")


def build_landscape(landscape_artifact: str | None = None) -> EmpiricalLandscapeModel:
    if landscape_artifact:
        return load_empirical_landscape(landscape_artifact)
    return EmpiricalLandscapeModel(
        tables_by_key={
            "channel:feed|global": EmpiricalTable(
                bids=[0.1, 0.5, 1.0, 1.5, 2.0, 3.0],
                win_probs=[0.05, 0.15, 0.32, 0.48, 0.62, 0.80],
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
        model_version="controller_sweep_empirical_v1",
    )


def build_engine(args: argparse.Namespace) -> DecisionEngine:
    predictor = build_predictor(args)
    default_directive = PacingDirective(
        pacing_multiplier=1.0,
        throttle_prob=1.0,
        shadow_lambda=None,
        reason="controller_sweep_default",
    )
    budget_provider = InMemoryBudgetStateProvider(states={}, default_directive=default_directive)
    return DecisionEngine(
        predictor=predictor,
        landscape_model=build_landscape(args.landscape_artifact),
        budget_state_provider=budget_provider,
        rank_scorer=ValueBasedRankScorer(use_landscape_in_score=False),
        allocator=TopKAllocator(),
    )


def _safe_div(x: float, y: float) -> float:
    return x / y if abs(y) > 1e-12 else 0.0


def summarize_run(
    per_auction: list[dict[str, Any]],
    controller_updates: list[dict[str, Any]],
    budget_amount: float,
    num_time_buckets: int,
) -> dict[str, Any]:
    spend_summary = build_spend_summary(per_auction, budget_amount=budget_amount)
    pacing_summary = build_pacing_summary(controller_updates)
    time_buckets = build_time_bucketed_pacing_diagnostics(per_auction, num_buckets=num_time_buckets)

    final_bucket = time_buckets[-1] if time_buckets else {}
    mean_abs_gap = _safe_div(
        sum(abs(float(row.get("realized_minus_target", 0.0))) for row in time_buckets),
        len(time_buckets),
    )
    mean_abs_ratio_error = _safe_div(
        sum(abs(1.0 - float(row.get("realized_to_target_ratio", 0.0))) for row in time_buckets if float(row.get("cumulative_target_spend", 0.0)) > 0),
        sum(1 for row in time_buckets if float(row.get("cumulative_target_spend", 0.0)) > 0),
    )
    clipped_rate = _safe_div(
        float(pacing_summary.get("num_clipped_updates", 0)),
        float(max(1, int(pacing_summary.get("num_updates", 0)))),
    )

    objective = (
        abs(1.0 - float(spend_summary.get("spend_attainment_ratio", 0.0))) * 100.0
        + mean_abs_ratio_error * 25.0
        + clipped_rate * 5.0
    )

    return {
        "objective": objective,
        "final_abs_gap": abs(float(final_bucket.get("realized_minus_target", 0.0))),
        "mean_abs_gap": mean_abs_gap,
        "mean_abs_ratio_error": mean_abs_ratio_error,
        "final_realized_to_target_ratio": float(final_bucket.get("realized_to_target_ratio", 0.0)),
        "spend_summary": spend_summary,
        "pacing_summary": pacing_summary,
        "time_bucket_tail": time_buckets[-3:],
    }


def run_one_config(args: argparse.Namespace, records, kp: float, interval_ms: int, curve_name: str) -> dict[str, Any]:
    engine = build_engine(args)
    controller = BoundedProportionalController(kp=kp)
    tracker = BudgetTracker(
        entity_id=args.entity_id,
        date=args.date,
        budget_amount=args.budget,
        desired_curve=build_curve(curve_name),
    )
    runner = BudgetReplayRunner(
        engine=engine,
        controller=controller,
        tracker=tracker,
        controller_update_interval_ms=interval_ms,
    )
    per_auction = runner.run(records)
    summary = summarize_run(
        per_auction=per_auction,
        controller_updates=runner.controller_updates,
        budget_amount=args.budget,
        num_time_buckets=args.num_time_buckets,
    )
    return {
        "config": {
            "kp": kp,
            "controller_update_interval_ms": interval_ms,
            "curve": curve_name,
        },
        **summary,
    }


def parse_float_list(raw: str) -> list[float]:
    return [float(x.strip()) for x in raw.split(",") if x.strip()]


def parse_int_list(raw: str) -> list[int]:
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


def parse_str_list(raw: str) -> list[str]:
    return [x.strip() for x in raw.split(",") if x.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep controller settings over historical replay logs")
    parser.add_argument("--logs-path", required=True)
    parser.add_argument("--bundle-dir")
    parser.add_argument("--predictor-mode", choices=["bundle", "oracle", "noisy_oracle"], default="oracle")
    parser.add_argument("--noise-sigma", type=float, default=0.5)
    parser.add_argument("--noise-bias", type=float, default=0.0)
    parser.add_argument("--budget", type=float, required=True)
    parser.add_argument("--kp-values", default="0.5,1.0,2.0,3.0")
    parser.add_argument("--controller-update-interval-ms-values", default="0,100,500,1000")
    parser.add_argument("--curve-values", default="uniform,frontloaded")
    parser.add_argument("--entity-id", default="global_budget")
    parser.add_argument("--date", default="1970-01-01")
    parser.add_argument("--default-num-slots", type=int, default=1)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--landscape-artifact")
    parser.add_argument("--num-time-buckets", type=int, default=20)
    parser.add_argument("--top-k", type=int, default=10)
    args = parser.parse_args()

    records = load_historical_replay_records(args.logs_path, default_num_slots=args.default_num_slots)
    kp_values = parse_float_list(args.kp_values)
    interval_values = parse_int_list(args.controller_update_interval_ms_values)
    curve_values = parse_str_list(args.curve_values)

    runs = [
        run_one_config(args, records, kp=kp, interval_ms=interval_ms, curve_name=curve_name)
        for kp, interval_ms, curve_name in itertools.product(kp_values, interval_values, curve_values)
    ]
    runs.sort(key=lambda row: (float(row["objective"]), float(row["final_abs_gap"])))

    output = {
        "search_space": {
            "kp_values": kp_values,
            "controller_update_interval_ms_values": interval_values,
            "curve_values": curve_values,
        },
        "num_runs": len(runs),
        "best_run": runs[0] if runs else None,
        "top_runs": runs[: max(1, args.top_k)],
        "all_runs": runs,
    }
    print(json.dumps(to_dict(output), indent=2))


if __name__ == "__main__":
    main()
