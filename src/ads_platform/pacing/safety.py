from __future__ import annotations

from ads_platform.common.utils import clip
from ads_platform.schemas.pacing import BudgetState, PacingDirective


def apply_step_limit(current_value: float, target_value: float, max_step_delta: float) -> float:
    lower = current_value - max_step_delta
    upper = current_value + max_step_delta
    return clip(target_value, lower, upper)


def is_state_stale(last_update_ts_ms: int, now_ts_ms: int, max_age_ms: int) -> bool:
    return (now_ts_ms - last_update_ts_ms) > max_age_ms


def safe_stale_directive(state: BudgetState, stale_throttle_prob: float = 0.5) -> PacingDirective:
    return PacingDirective(
        pacing_multiplier=min(state.pacing_multiplier, 1.0),
        throttle_prob=stale_throttle_prob,
        shadow_lambda=state.shadow_lambda,
        reason="stale_state_safe_mode",
        debug={"entity_id": state.entity_id},
    )
