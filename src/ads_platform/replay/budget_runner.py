from __future__ import annotations

from ads_platform.decisioning.engine import DecisionEngine
from ads_platform.pacing.controllers import BoundedProportionalController
from ads_platform.pacing.state import ControllerState
from ads_platform.pacing.updater import BudgetTracker
from ads_platform.replay.runner import ReplayRunner


class BudgetReplayRunner:
    def __init__(self, engine: DecisionEngine, controller: BoundedProportionalController, tracker: BudgetTracker):
        self.engine = engine
        self.controller = controller
        self.tracker = tracker
        self.controller_state = ControllerState(entity_id=tracker.entity_id, date=tracker.date)
        self.controller_updates: list[dict] = []

    def _update_provider_state(self, timestamp_ms: int) -> None:
        budget_state = self.tracker.to_budget_state(self.controller_state, timestamp_ms)
        directive = self.controller.update(budget_state)
        was_clipped = abs(directive.pacing_multiplier - budget_state.pacing_multiplier) >= self.controller.max_step_delta - 1e-12
        self.controller_updates.append({
            "timestamp_ms": timestamp_ms,
            "pacing_multiplier": directive.pacing_multiplier,
            "throttle_prob": directive.throttle_prob,
            "reason": directive.reason,
            "error": directive.debug.get("error", 0.0),
            "was_clipped": was_clipped,
        })
        next_state = ControllerState(
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
        self.controller_state = next_state
        provider_state = self.tracker.to_budget_state(self.controller_state, timestamp_ms)
        self.engine.budget_state_provider.states[self.tracker.entity_id] = provider_state

    def run(self, records):
        ordered_records = sorted(records, key=lambda r: r.auction_input.request.timestamp_ms)
        per_auction = []
        for record in ordered_records:
            timestamp_ms = record.auction_input.request.timestamp_ms
            self._update_provider_state(timestamp_ms)
            result = self.engine.decide(record.auction_input, num_slots=record.num_slots)
            logs = self.engine.build_decision_logs(record.auction_input, result)
            selected_logs = [row for row in logs if row.selected]
            spend_delta = sum(record.observed_spend_by_ad_id.get(row.ad_id, row.estimated_cost or 0.0) for row in selected_logs)
            click_delta = sum(1 for row in selected_logs if row.ad_id in record.observed_clicked_ad_ids)
            self.tracker.apply_observation(spend_delta=spend_delta, clicks_delta=click_delta)
            auction_payload = ReplayRunner._auction_result_dict(record, logs)
            snapshot = self.tracker.snapshot(timestamp_ms)
            auction_payload.update({
                "spend_so_far_after": self.tracker.spend_so_far,
                "target_spend_so_far": snapshot.target_spend_so_far,
                "controller_pacing_multiplier": self.controller_state.pacing_multiplier,
            })
            per_auction.append(auction_payload)
        return per_auction
