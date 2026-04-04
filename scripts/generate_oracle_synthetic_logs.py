from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def make_candidate(auction_idx: int, cand_idx: int, rng: random.Random) -> dict:
    device = rng.choice(["mobile", "desktop", "tablet"])
    hour = rng.randint(0, 23)
    segment_id = rng.randint(0, 9)
    base_bid = rng.uniform(0.5, 2.0)
    historical_ctr = rng.uniform(0.01, 0.25)
    campaign_id = f"camp_{cand_idx % 4}"
    adgroup_id = f"ag_{cand_idx % 8}"

    device_effect = {"mobile": 0.25, "desktop": -0.05, "tablet": 0.1}[device]
    hour_effect = 0.25 if 18 <= hour <= 22 else (-0.1 if 1 <= hour <= 6 else 0.0)
    segment_effect = (segment_id - 4.5) * 0.08
    bid_effect = 0.55 * math.log1p(base_bid)
    hist_effect = 2.0 * (historical_ctr - 0.08)
    oracle_pctr = sigmoid(-2.4 + device_effect + hour_effect + segment_effect + bid_effect + hist_effect)

    return {
        "ad_id": f"req_{auction_idx}_ad_{cand_idx}",
        "campaign_id": campaign_id,
        "adgroup_id": adgroup_id,
        "base_bid": base_bid,
        "features": {
            "device": device,
            "hour": hour,
            "historical_ctr": historical_ctr,
        },
        "extra": {
            "segment_id": segment_id,
        },
        "_oracle_pctr": oracle_pctr,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic auction logs with oracle CTR labels")
    parser.add_argument("--output-path", default="data/historical_auctions_oracle.jsonl")
    parser.add_argument("--num-auctions", type=int, default=10000)
    parser.add_argument("--num-candidates", type=int, default=5)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as handle:
        for auction_idx in range(args.num_auctions):
            request = {
                "request_id": f"req_{auction_idx}",
                "timestamp_ms": 1775193063359 + auction_idx,
                "device_type": rng.choice(["mobile", "desktop"]),
                "country": "US",
                "placement": rng.choice(["feed", "search", "video"]),
                "app_or_site": "demo_app",
            }

            candidates = [make_candidate(auction_idx, cand_idx, rng) for cand_idx in range(args.num_candidates)]
            outcomes = []
            for candidate in candidates:
                oracle_pctr = candidate.pop("_oracle_pctr")
                clicked = int(rng.random() < oracle_pctr)
                price = rng.uniform(0.15, max(0.16, candidate["base_bid"] * 0.95))
                outcomes.append({
                    "clicked": clicked,
                    "price": price,
                    "true_pctr": oracle_pctr,
                })

            handle.write(json.dumps({
                "request": request,
                "candidates": candidates,
                "outcomes": outcomes,
            }) + "\n")

    print(f"Wrote {args.num_auctions} auctions to {output_path}")


if __name__ == "__main__":
    main()
