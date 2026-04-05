from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ads_platform.decisioning.engine import DecisionEngine
from ads_platform.schemas.logs import DecisionLog, ReplayDecisionLog
from ads_platform.schemas.request import AuctionInput


@dataclass(slots=True)
class ReplayRecord:
    auction_input: AuctionInput
    num_slots: int
    observed_clicked_ad_ids: list[str] = field(default_factory=list)
    observed_spend_by_ad_id: dict[str, float] = field(default_factory=dict)
    record_id: str | None = None


@dataclass(slots=True)
class ReplaySummary:
    num_auctions: int
    num_candidates: int
    num_winners: int
    predicted_clicks: float
    observed_clicks_on_selected: int
    realized_spend: float
    avg_predicted_ctr_selected: float
    avg_effective_bid_selected: float


class ReplayRunner:
    def __init__(self, engine: DecisionEngine):
        self.engine = engine

    def run(self, records: list[ReplayRecord]) -> tuple[ReplaySummary, list[dict[str, Any]]]:
        num_candidates = 0
        num_winners = 0
        predicted_clicks = 0.0
        observed_clicks_on_selected = 0
        realized_spend = 0.0
        sum_selected_pctr = 0.0
        sum_selected_bid = 0.0
        per_auction: list[dict[str, Any]] = []

        for record in records:
            result = self.engine.decide(record.auction_input, num_slots=record.num_slots)
            logs = self.engine.build_decision_logs(record.auction_input, result)
            selected_logs = [row for row in logs if row.selected]

            num_candidates += len(record.auction_input.candidates)
            num_winners += len(selected_logs)
            predicted_clicks += sum(row.pctr_calibrated for row in selected_logs)
            sum_selected_pctr += sum(row.pctr_calibrated for row in selected_logs)
            sum_selected_bid += sum(row.bid_effective for row in selected_logs)
            realized_spend += sum(record.observed_spend_by_ad_id.get(row.ad_id, row.estimated_cost or 0.0) for row in selected_logs)
            observed_clicks_on_selected += sum(1 for row in selected_logs if row.ad_id in record.observed_clicked_ad_ids)

            per_auction.append(self._auction_result_dict(record, logs))

        summary = ReplaySummary(
            num_auctions=len(records),
            num_candidates=num_candidates,
            num_winners=num_winners,
            predicted_clicks=predicted_clicks,
            observed_clicks_on_selected=observed_clicks_on_selected,
            realized_spend=realized_spend,
            avg_predicted_ctr_selected=(sum_selected_pctr / num_winners) if num_winners else 0.0,
            avg_effective_bid_selected=(sum_selected_bid / num_winners) if num_winners else 0.0,
        )
        return summary, per_auction

    @staticmethod
    def _auction_result_dict(record: ReplayRecord, logs: list[DecisionLog]) -> dict[str, Any]:
        selected = [row for row in logs if row.selected]

        replay_logs: list[dict[str, Any]] = []
        clicked_set = set(record.observed_clicked_ad_ids)
        spend_by_ad_id = record.observed_spend_by_ad_id

        for row in logs:
            replay_row = ReplayDecisionLog(
                **row.model_dump(),
                observed_clicked=int(row.ad_id in clicked_set),
                realized_spend=float(spend_by_ad_id.get(row.ad_id, row.estimated_cost or 0.0)),
            )
            replay_logs.append(replay_row.model_dump(mode="json"))

        return {
            "record_id": record.record_id or record.auction_input.request.request_id,
            "request_id": record.auction_input.request.request_id,
            "selected_ad_ids": [row.ad_id for row in selected],
            "predicted_clicks": sum(row.pctr_calibrated for row in selected),
            "observed_clicks_on_selected": sum(1 for row in selected if row.ad_id in clicked_set),
            "realized_spend": sum(spend_by_ad_id.get(row.ad_id, row.estimated_cost or 0.0) for row in selected),
            "decision_logs": replay_logs,
        }