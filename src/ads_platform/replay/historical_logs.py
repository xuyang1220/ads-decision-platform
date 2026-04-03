from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ads_platform.replay.runner import ReplayRecord
from ads_platform.schemas.request import AdCandidate, AuctionInput, RequestContext


def _candidate_from_payload(payload: dict[str, Any]) -> AdCandidate:
    return AdCandidate(
        ad_id=str(payload["ad_id"]),
        campaign_id=str(payload["campaign_id"]),
        adgroup_id=str(payload.get("adgroup_id", payload["campaign_id"])),
        advertiser_id=(None if payload.get("advertiser_id") is None else str(payload.get("advertiser_id"))),
        base_bid=float(payload.get("base_bid", 1.0)),
        features=dict(payload.get("features", {})),
        extra=dict(payload.get("extra", {})),
    )


def _request_from_payload(payload: dict[str, Any], default_request_id: str) -> RequestContext:
    return RequestContext(
        request_id=str(payload.get("request_id", default_request_id)),
        timestamp_ms=int(payload.get("timestamp_ms", 0)),
        user_id=payload.get("user_id"),
        device_type=str(payload.get("device_type", payload.get("device", "unknown"))),
        country=str(payload.get("country", "unknown")),
        placement=str(payload.get("placement", "unknown")),
        app_or_site=str(payload.get("app_or_site", payload.get("site", "unknown"))),
        extra=dict(payload.get("extra", {})),
    )


def record_from_json(payload: dict[str, Any], default_num_slots: int = 1) -> ReplayRecord:
    request_payload = payload.get("request") or {}
    record_id = str(payload.get("record_id", request_payload.get("request_id", "record")))
    request = _request_from_payload(request_payload, default_request_id=record_id)
    candidates_payload = list(payload.get("candidates", []))
    candidates = [_candidate_from_payload(candidate) for candidate in candidates_payload]

    observed_clicked_ad_ids: list[str] = []
    observed_spend_by_ad_id: dict[str, float] = {}

    # Format 1: explicit observed block
    observed = payload.get("observed", {})
    if "clicked_ad_ids" in observed:
        observed_clicked_ad_ids = [str(ad_id) for ad_id in observed.get("clicked_ad_ids", [])]
    if "spend_by_ad_id" in observed:
        observed_spend_by_ad_id = {str(k): float(v) for k, v in observed.get("spend_by_ad_id", {}).items()}

    # Format 2: per-candidate embedded fields
    if not observed_clicked_ad_ids and not observed_spend_by_ad_id:
        for candidate_payload in candidates_payload:
            ad_id = str(candidate_payload["ad_id"])
            if candidate_payload.get("clicked"):
                observed_clicked_ad_ids.append(ad_id)
            if "realized_spend" in candidate_payload:
                observed_spend_by_ad_id[ad_id] = float(candidate_payload["realized_spend"])

    # Format 3: parallel outcomes list aligned with candidates by index
    if not observed_clicked_ad_ids and not observed_spend_by_ad_id:
        outcomes_payload = list(payload.get("outcomes", []))
        if outcomes_payload:
            if len(outcomes_payload) != len(candidates_payload):
                raise ValueError(
                    f"Length mismatch: {len(candidates_payload)} candidates but "
                    f"{len(outcomes_payload)} outcomes for record_id={record_id}"
                )
            for candidate_payload, outcome_payload in zip(candidates_payload, outcomes_payload):
                ad_id = str(candidate_payload["ad_id"])

                clicked = int(outcome_payload.get("clicked", outcome_payload.get("click", 0)))
                price = float(outcome_payload.get("price", outcome_payload.get("cost", 0.0)))

                if clicked:
                    observed_clicked_ad_ids.append(ad_id)

                observed_spend_by_ad_id[ad_id] = price

    return ReplayRecord(
        auction_input=AuctionInput(request=request, candidates=candidates),
        num_slots=int(payload.get("num_slots", default_num_slots)),
        observed_clicked_ad_ids=observed_clicked_ad_ids,
        observed_spend_by_ad_id=observed_spend_by_ad_id,
        record_id=record_id,
    )


def load_historical_replay_records(path: str | Path, default_num_slots: int = 1) -> list[ReplayRecord]:
    records: list[ReplayRecord] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            try:
                records.append(record_from_json(payload, default_num_slots=default_num_slots))
            except Exception as exc:  # pragma: no cover - line context enrichment
                raise ValueError(f"Failed to parse historical log line {line_no}: {exc}") from exc
    return records
