from __future__ import annotations

import argparse
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
        model_version="shadow_replay_empirical_v1",
    )


def build_engine(args: argparse.Namespace) -> DecisionEngine:
    predictor = build_predictor(args)
    default_directive = PacingDirective(
        pacing_multiplier=1.0,
        throttle_prob=1.0,
        shadow_lambda=None,
        reason="shadow_default",
    )
    budget_provider = InMemoryBudgetStateProvider(states={}, default_directive=default_directive)
    return DecisionEngine(
        predictor=predictor,
        landscape_model=build_landscape(args.landscape_artifact),
        budget_state_provider=budget_provider,
        rank_scorer=ValueBasedRankScorer(use_landscape_in_score=False),
        allocator=TopKAllocator(),
    )


def build_shadow_auction_rows(per_auction: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for auction in per_auction:
        selected = [row for row in auction.get("decision_logs", []) if row.get("selected")]
        selected_ad_ids = [str(row.get("ad_id")) for row in selected]
        inferred_prod_winner_ids = [
            str(row.get("ad_id"))
            for row in auction.get("decision_logs", [])
            if float(row.get("realized_spend", 0.0)) > 0.0
        ]
        avg_pctr = sum(float(row.get("pctr_calibrated", 0.0)) for row in selected) / len(selected) if selected else 0.0
        avg_bid = sum(float(row.get("bid_effective", 0.0)) for row in selected) / len(selected) if selected else 0.0
        avg_estimated_cost = sum(float(row.get("estimated_cost", 0.0)) for row in selected) / len(selected) if selected else 0.0
        avg_pacing_multiplier = sum(float(row.get("pacing_multiplier", 0.0)) for row in selected) / len(selected) if selected else 0.0
        avg_throttle_prob = sum(float(row.get("throttle_prob", 0.0)) for row in selected) / len(selected) if selected else 0.0
        overlap = len(set(selected_ad_ids) & set(inferred_prod_winner_ids))
        union = len(set(selected_ad_ids) | set(inferred_prod_winner_ids))
        rows.append(
            {
                "request_id": auction.get("request_id"),
                "timestamp_ms": int(auction.get("timestamp_ms", 0)),
                "shadow_selected_ad_ids": selected_ad_ids,
                "inferred_prod_winner_ad_ids": inferred_prod_winner_ids,
                "shadow_num_winners": len(selected_ad_ids),
                "shadow_predicted_spend": float(auction.get("predicted_spend", 0.0)),
                "shadow_realized_spend": float(auction.get("realized_spend", 0.0)),
                "target_spend_so_far": float(auction.get("target_spend_so_far", 0.0)),
                "spend_so_far_before": float(auction.get("spend_so_far_before", 0.0)),
                "spend_so_far_after": float(auction.get("spend_so_far_after", 0.0)),
                "avg_selected_pctr": avg_pctr,
                "avg_selected_effective_bid": avg_bid,
                "avg_selected_estimated_cost": avg_estimated_cost,
                "avg_selected_pacing_multiplier": avg_pacing_multiplier,
                "avg_selected_throttle_prob": avg_throttle_prob,
                "winner_overlap_jaccard": (overlap / union) if union > 0 else 0.0,
            }
        )
    return rows


def build_shadow_summary(
    per_auction: list[dict[str, Any]],
    controller_updates: list[dict[str, Any]],
    budget_amount: float,
    num_time_buckets: int,
) -> dict[str, Any]:
    auction_rows = build_shadow_auction_rows(per_auction)
    time_buckets = build_time_bucketed_pacing_diagnostics(per_auction, num_buckets=num_time_buckets)
    overlap_rows = [float(row["winner_overlap_jaccard"]) for row in auction_rows]
    return {
        "budget_summary": build_spend_summary(per_auction, budget_amount=budget_amount),
        "controller_summary": build_pacing_summary(controller_updates),
        "auction_summary": {
            "num_auctions": len(auction_rows),
            "avg_shadow_winners_per_auction": (
                sum(int(row["shadow_num_winners"]) for row in auction_rows) / len(auction_rows)
                if auction_rows else 0.0
            ),
            "avg_winner_overlap_jaccard": (sum(overlap_rows) / len(overlap_rows)) if overlap_rows else 0.0,
            "shadow_spend_per_auction": (
                sum(float(row["shadow_realized_spend"]) for row in auction_rows) / len(auction_rows)
                if auction_rows else 0.0
            ),
        },
        "time_bucket_tail": time_buckets[-5:],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run replay in shadow mode and emit monitoring-friendly output")
    parser.add_argument("--logs-path", required=True)
    parser.add_argument("--output-path")
    parser.add_argument("--bundle-dir")
    parser.add_argument("--predictor-mode", choices=["bundle", "oracle", "noisy_oracle"], default="oracle")
    parser.add_argument("--noise-sigma", type=float, default=0.5)
    parser.add_argument("--noise-bias", type=float, default=0.0)
    parser.add_argument("--budget", type=float, required=True)
    parser.add_argument("--curve", choices=["uniform", "frontloaded"], default="uniform")
    parser.add_argument("--kp", type=float, default=1.0)
    parser.add_argument("--controller-update-interval-ms", type=int, default=500)
    parser.add_argument("--entity-id", default="global_budget")
    parser.add_argument("--date", default="1970-01-01")
    parser.add_argument("--default-num-slots", type=int, default=1)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--landscape-artifact")
    parser.add_argument("--num-time-buckets", type=int, default=20)
    args = parser.parse_args()

    records = load_historical_replay_records(args.logs_path, default_num_slots=args.default_num_slots)
    engine = build_engine(args)
    controller = BoundedProportionalController(kp=args.kp)
    tracker = BudgetTracker(
        entity_id=args.entity_id,
        date=args.date,
        budget_amount=args.budget,
        desired_curve=build_curve(args.curve),
    )
    runner = BudgetReplayRunner(
        engine=engine,
        controller=controller,
        tracker=tracker,
        controller_update_interval_ms=args.controller_update_interval_ms,
    )
    per_auction = runner.run(records)

    output = {
        "config": {
            "predictor_mode": args.predictor_mode,
            "budget": args.budget,
            "curve": args.curve,
            "kp": args.kp,
            "controller_update_interval_ms": args.controller_update_interval_ms,
            "landscape_artifact": args.landscape_artifact,
        },
        "summary": build_shadow_summary(
            per_auction=per_auction,
            controller_updates=runner.controller_updates,
            budget_amount=args.budget,
            num_time_buckets=args.num_time_buckets,
        ),
        "controller_updates": runner.controller_updates,
        "shadow_auctions": build_shadow_auction_rows(per_auction),
    }

    payload = json.dumps(to_dict(output), indent=2)
    if args.output_path:
        with open(args.output_path, "w", encoding="utf-8") as handle:
            handle.write(payload)
    else:
        print(payload)


if __name__ == "__main__":
    main()
