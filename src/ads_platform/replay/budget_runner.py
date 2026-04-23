from __future__ import annotations

from ads_platform.decisioning.engine import DecisionEngine
from ads_platform.pacing.controllers import BoundedProportionalController
from ads_platform.pacing.state import ControllerState
from ads_platform.pacing.updater import BudgetTracker


class BudgetReplayRunner:
    def __init__(
        self,
        engine: DecisionEngine,
        controller: BoundedProportionalController,
        tracker: BudgetTracker,
    ):
        self.engine = engine
        self.controller = controller
        self.tracker = tracker
        self.controller_state = ControllerState(
            entity_id=tracker.entity_id,
            date=tracker.date,
        )
        self.controller_updates: list[dict] = []

    def _update_provider_state(self, timestamp_ms: int, campaign_ids: set[str] | None = None) -> None:
        budget_state = self.tracker.to_budget_state(self.controller_state, timestamp_ms)
        directive = self.controller.update(budget_state)

        was_clipped = (
            abs(directive.pacing_multiplier - budget_state.pacing_multiplier)
            >= self.controller.max_step_delta - 1e-12
        )

        self.controller_updates.append(
            {
                "timestamp_ms": timestamp_ms,
                "pacing_multiplier": directive.pacing_multiplier,
                "throttle_prob": directive.throttle_prob,
                "reason": directive.reason,
                "error": directive.debug.get("error", 0.0),
                "was_clipped": was_clipped,
            }
        )

        self.controller_state = ControllerState(
            entity_id=self.controller_state.entity_id,
            date=self.controller_state.date,
            pacing_multiplier=directive.pacing_multiplier,
            throttle_prob=directive.throttle_prob,
            shadow_lambda=directive.shadow_lambda,
            last_update_ts_ms=timestamp_ms,
            stale=False,
            integral_error=self.controller_state.integral_error,
            debug={"reason": directive.reason},
        )

        provider_state = self.tracker.to_budget_state(self.controller_state, timestamp_ms)
        self.engine.budget_state_provider.states[self.tracker.entity_id] = provider_state
        for campaign_id in campaign_ids or set():
            self.engine.budget_state_provider.states[campaign_id] = provider_state

    def run(self, records, num_slots: int = 1) -> list[dict]:
        sorted_records = sorted(records, key=lambda r: r.auction_input.request.timestamp_ms)
        if sorted_records:
            self.tracker.set_replay_window(
                sorted_records[0].auction_input.request.timestamp_ms,
                sorted_records[-1].auction_input.request.timestamp_ms,
            )

        per_auction_results: list[dict] = []
        prev_target_spend_so_far = 0.0

        for record in sorted_records:
            ts_ms = record.auction_input.request.timestamp_ms
            campaign_ids = {candidate.campaign_id for candidate in record.auction_input.candidates}

            # 1) Update controller/provider state for this timestamp
            self._update_provider_state(ts_ms, campaign_ids=campaign_ids)

            # 2) Read budget state after controller update
            budget_state = self.engine.budget_state_provider.states[self.tracker.entity_id]
            current_target_spend_so_far = float(budget_state.target_spend_so_far)
            spend_so_far_before = float(budget_state.spend_so_far)

            target_spend_increment = max(
                0.0,
                current_target_spend_so_far - prev_target_spend_so_far,
            )

            # 3) Run decision engine
            result = self.engine.decide(record.auction_input, num_slots=num_slots)
            logs = self.engine.build_decision_logs(record.auction_input, result)

            selected_logs = [row for row in logs if row.selected]

            predicted_spend_selected = sum(
                float(row.estimated_cost or 0.0) for row in selected_logs
            )
            realized_spend_selected = sum(
                float(record.observed_spend_by_ad_id.get(row.ad_id, 0.0))
                for row in selected_logs
            )
            observed_clicks_selected = sum(
                1 for row in selected_logs if row.ad_id in record.observed_clicked_ad_ids
            )

            # 4) Update tracker with realized outcomes
            self.tracker.apply_observation(
                spend_delta=realized_spend_selected,
                clicks_delta=observed_clicks_selected,
            )

            spend_so_far_after = self.tracker.spend_so_far

            # 5) Build replay-enriched logs
            clicked_set = set(record.observed_clicked_ad_ids)
            spend_by_ad_id = record.observed_spend_by_ad_id

            replay_logs = []
            for row in logs:
                payload = row.model_dump(mode="json")
                payload["observed_clicked"] = int(row.ad_id in clicked_set)
                payload["realized_spend"] = float(spend_by_ad_id.get(row.ad_id, 0.0))
                replay_logs.append(payload)

            # 6) Auction-level replay result
            auction_result = {
                "record_id": record.record_id or record.auction_input.request.request_id,
                "request_id": record.auction_input.request.request_id,
                "timestamp_ms": ts_ms,
                "predicted_spend": predicted_spend_selected,
                "realized_spend": realized_spend_selected,
                "target_spend_increment": target_spend_increment,
                "target_spend_so_far": current_target_spend_so_far,
                "spend_so_far_before": spend_so_far_before,
                "spend_so_far_after": spend_so_far_after,
                "decision_logs": replay_logs,
            }
            per_auction_results.append(auction_result)

            prev_target_spend_so_far = current_target_spend_so_far

        return per_auction_results
