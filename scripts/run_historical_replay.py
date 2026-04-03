from __future__ import annotations

import argparse
import json

from ads_platform.ctr.bundle import CTRBundleLoader
from ads_platform.landscape.empirical import EmpiricalLandscapeModel, SegmentCurve
from ads_platform.pacing.providers import InMemoryBudgetStateProvider
from ads_platform.ranking.multislot import TopKAllocator
from ads_platform.ranking.scoring import ValueBasedRankScorer
from ads_platform.replay.historical_logs import load_historical_replay_records
from ads_platform.replay.runner import ReplayRunner
from ads_platform.decisioning.engine import DecisionEngine
from ads_platform.schemas.pacing import BudgetState, PacingDirective
from dataclasses import asdict


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay historical auction logs against a trained bundle")
    parser.add_argument("--bundle-dir", required=True)
    parser.add_argument("--logs-path", required=True, help="JSONL file with one auction record per line")
    parser.add_argument("--default-num-slots", type=int, default=1)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    bundle = CTRBundleLoader.load(args.bundle_dir, device=args.device)
    default_directive = PacingDirective(pacing_multiplier=1.0, throttle_prob=1.0, shadow_lambda=None, reason="replay_default")
    budget_provider = InMemoryBudgetStateProvider(
        states={},
        default_directive=default_directive,
    )
    landscape_model = EmpiricalLandscapeModel(
        curves_by_segment={None: SegmentCurve(slope=1.2, midpoint=1.0, cost_fraction=0.7)},
        default_curve=SegmentCurve(slope=1.2, midpoint=1.0, cost_fraction=0.7),
        model_version="replay_empirical_v1",
    )
    engine = DecisionEngine(
        predictor=bundle.predictor,
        landscape_model=landscape_model,
        budget_state_provider=budget_provider,
        rank_scorer=ValueBasedRankScorer(use_landscape_in_score=False),
        allocator=TopKAllocator(),
    )
    records = load_historical_replay_records(args.logs_path, default_num_slots=args.default_num_slots)
    # print("num_records =", len(records))
    # for r in records:
    #     if not r.observed_spend_by_ad_id:
    #         print("sample_record =", r)
    #         break
    summary, per_auction = ReplayRunner(engine).run(records)
    print(json.dumps({"summary": asdict(summary), "num_auction_details": len(per_auction)}, indent=2))


if __name__ == "__main__":
    main()

