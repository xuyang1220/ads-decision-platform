import json
import random
from pathlib import Path
from datetime import datetime

NUM_AUCTIONS = 10000
NUM_CANDIDATES = 5

def random_candidate(i):
    return {
        "ad_id": f"ad_{i}",
        "campaign_id": f"camp_{i % 3}",
        "adgroup_id": f"ag_{i % 5}",
        "base_bid": random.uniform(0.5, 2.0),
        "features": {
            "device": random.choice(["mobile", "desktop"]),
            "hour": random.randint(0, 23),
        },
        "extra": {
            "segment_id": random.randint(0, 10)
        }
    }

def simulate_outcome(candidate):
    pctr = random.uniform(0.01, 0.3)
    clicked = int(random.random() < pctr)
    price = random.uniform(0.1, candidate["base_bid"])
    return {
        "clicked": clicked,
        "price": price
    }

def generate():
    output_path = Path("data/historical_auctions.jsonl")
    output_path.parent.mkdir(exist_ok=True)

    with open(output_path, "w") as f:
        for i in range(NUM_AUCTIONS):
            request = {
                "request_id": f"req_{i}",
                "timestamp_ms": int(datetime.utcnow().timestamp() * 1000),
                "device_type": "mobile",
                "country": "US",
                "placement": "feed",
                "app_or_site": "demo_app"
            }

            candidates = [random_candidate(j) for j in range(NUM_CANDIDATES)]

            outcomes = [
                simulate_outcome(c) for c in candidates
            ]

            record = {
                "request": request,
                "candidates": candidates,
                "outcomes": outcomes
            }

            f.write(json.dumps(record) + "\n")

    print(f"Generated {NUM_AUCTIONS} auctions at {output_path}")

if __name__ == "__main__":
    generate()