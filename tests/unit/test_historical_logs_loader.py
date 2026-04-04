from pathlib import Path

from ads_platform.replay.historical_logs import load_historical_replay_records


def test_load_historical_records_supports_parallel_outcomes(tmp_path: Path) -> None:
    path = tmp_path / "logs.jsonl"
    path.write_text(
        '\n'.join([
            '{"request": {"request_id": "req_1", "device_type": "mobile", "country": "US", "placement": "feed", "app_or_site": "demo"}, "candidates": [{"ad_id": "a1", "campaign_id": "c1", "adgroup_id": "g1", "base_bid": 1.0}], "outcomes": [{"clicked": 1, "price": 0.5, "true_pctr": 0.2}]}'
        ])
    )

    records = load_historical_replay_records(path)
    assert len(records) == 1
    record = records[0]
    assert record.observed_clicked_ad_ids == ["a1"]
    assert record.observed_spend_by_ad_id == {"a1": 0.5}
    assert record.auction_input.candidates[0].extra["oracle_pctr"] == 0.2
