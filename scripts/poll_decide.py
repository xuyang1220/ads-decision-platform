#!/usr/bin/env python3
"""Send randomized POST /decide requests on a fixed interval."""

from __future__ import annotations

import argparse
import json
import random
import string
import sys
import time
import urllib.error
import urllib.request
from typing import Any

INT_FEATURES = [f"I{i}" for i in range(1, 14)]
CAT_FEATURES = [f"C{i}" for i in range(1, 27)]
DEVICE_TYPES = ("mobile", "desktop", "tablet")
COUNTRIES = ("US", "GB", "DE", "FR", "CA")
PLACEMENTS = ("feed", "youtube", "email")


def _rand_id(prefix: str) -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"{prefix}_{suffix}"


def _rand_cat_value() -> str:
    return "".join(random.choices(string.ascii_lowercase, k=3))


def build_payload() -> dict[str, Any]:
    features: dict[str, str] = {
        name: str(random.randint(1, 100)) for name in INT_FEATURES
    }
    features.update({name: _rand_cat_value() for name in CAT_FEATURES})

    return {
        "request": {
            "request_id": _rand_id("quick_test"),
            "timestamp_ms": int(time.time() * 1000),
            "device_type": random.choice(DEVICE_TYPES),
            "country": random.choice(COUNTRIES),
            "placement": random.choice(PLACEMENTS),
            "app_or_site": _rand_id("app"),
        },
        "candidates": [
            {
                "ad_id": _rand_id("ad"),
                "campaign_id": _rand_id("cmp"),
                "adgroup_id": _rand_id("ag"),
                "base_bid": round(random.uniform(0.5, 3.0), 2),
                "features": features,
            }
        ],
    }


def post_decide(url: str, payload: dict[str, Any], timeout_s: float) -> tuple[int, str]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        default="http://localhost:8000/decide",
        help="Decide API URL (default: %(default)s)",
    )
    parser.add_argument(
        "--interval-minutes",
        type=float,
        default=5.0,
        metavar="X",
        help="Minutes between requests (default: %(default)s)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds (default: %(default)s)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Send a single request and exit",
    )
    args = parser.parse_args()

    if args.interval_minutes <= 0:
        parser.error("--interval-minutes must be positive")

    interval_s = args.interval_minutes * 60.0
    print(
        f"Polling {args.url} every {args.interval_minutes} min "
        f"({interval_s:.0f}s). Ctrl+C to stop.",
        flush=True,
    )

    attempt = 0
    while True:
        attempt += 1
        payload = build_payload()
        request_id = payload["request"]["request_id"]
        try:
            status, body = post_decide(args.url, payload, args.timeout)
            print(
                f"[{attempt}] {request_id} -> HTTP {status} "
                f"({len(body)} bytes)",
                flush=True,
            )
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            print(
                f"[{attempt}] {request_id} -> HTTP {exc.code}: {err_body[:200]}",
                file=sys.stderr,
                flush=True,
            )
        except urllib.error.URLError as exc:
            print(f"[{attempt}] {request_id} -> error: {exc.reason}", file=sys.stderr, flush=True)

        if args.once:
            break

        try:
            time.sleep(interval_s)
        except KeyboardInterrupt:
            print("\nStopped.", flush=True)
            break

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
