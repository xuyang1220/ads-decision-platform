from __future__ import annotations

import argparse
import json

from ads_platform.common.serialization import to_dict
from ads_platform.landscape.fit_empirical import FitConfig, fit_empirical_artifact_from_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Fit an empirical bid landscape artifact from replay/simulator JSONL logs")
    parser.add_argument("--logs-path", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--model-version", default="fitted_empirical_v1")
    parser.add_argument("--min-rows-per-key", type=int, default=20)
    parser.add_argument("--num-bid-bins", type=int, default=6)
    parser.add_argument("--include-segment-keys", action="store_true")
    parser.add_argument("--include-adgroup-keys", action="store_true")
    parser.add_argument("--include-campaign-keys", action="store_true")
    parser.add_argument("--no-channel-keys", action="store_true")
    parser.add_argument("--no-global-key", action="store_true")
    args = parser.parse_args()

    artifact = fit_empirical_artifact_from_jsonl(
        args.logs_path,
        config=FitConfig(
            min_rows_per_key=args.min_rows_per_key,
            num_bid_bins=args.num_bid_bins,
            include_segment_keys=args.include_segment_keys,
            include_adgroup_keys=args.include_adgroup_keys,
            include_campaign_keys=args.include_campaign_keys,
            include_channel_keys=not args.no_channel_keys,
            include_global_key=not args.no_global_key,
            model_version=args.model_version,
        ),
    )
    artifact.write_json(args.output_path)
    print(json.dumps(to_dict(artifact.metadata or {}), indent=2))


if __name__ == "__main__":
    main()
