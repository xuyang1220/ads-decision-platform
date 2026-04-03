from __future__ import annotations

from pathlib import Path

from ads_platform.replay.historical_logs import load_historical_replay_records


def test_load_historical_replay_records(tmp_path: Path) -> None:
    logs_path = tmp_path / "auctions.jsonl"
    logs_path.write_text(
        '{"record_id":"r1","request":{"request_id":"req-1","timestamp_ms":1,"device_type":"mobile","country":"US","placement":"feed","app_or_site":"example.com"},"num_slots":1,"candidates":[{"ad_id":"a1","campaign_id":"c1","adgroup_id":"g1","base_bid":1.2,"features":{"I1":"1","C1":"abc"},"clicked":1,"realized_spend":0.7}]}'
    )
    records = load_historical_replay_records(logs_path)
    assert len(records) == 1
    assert records[0].auction_input.request.request_id == "req-1"
    assert records[0].observed_clicked_ad_ids == ["a1"]
    assert records[0].observed_spend_by_ad_id["a1"] == 0.7
