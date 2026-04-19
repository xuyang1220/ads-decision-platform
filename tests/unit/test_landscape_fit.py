from __future__ import annotations

import json

from ads_platform.landscape.fit_empirical import FitConfig, fit_empirical_artifact_from_jsonl


def test_fit_empirical_artifact_from_jsonl(tmp_path):
    path = tmp_path / "logs.jsonl"
    rows = []
    for i in range(30):
        bid = 0.5 + 0.05 * i
        rows.append({
            "request": {
                "request_id": f"req_{i}",
                "placement": "feed",
            },
            "candidates": [
                {
                    "ad_id": f"ad_{i}",
                    "campaign_id": "camp_1",
                    "adgroup_id": "ag_1",
                    "base_bid": bid,
                    "extra": {"segment_id": 1},
                }
            ],
            "outcomes": [
                {
                    "won": 1,
                    "price": 0.25 * bid,
                }
            ],
        })
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")

    artifact = fit_empirical_artifact_from_jsonl(
        path,
        FitConfig(
            min_rows_per_key=5,
            num_bid_bins=4,
            include_channel_keys=True,
            include_global_key=True,
            include_segment_keys=False,
            include_adgroup_keys=False,
            include_campaign_keys=False,
            model_version="fitted_test_v1",
        ),
    )
    assert "channel:feed|global" in artifact.tables_by_key
    table = artifact.tables_by_key["channel:feed|global"]
    assert len(table.bids) >= 2
    assert table.win_probs[-1] >= table.win_probs[0]
    assert table.expected_costs[-1] >= table.expected_costs[0]
