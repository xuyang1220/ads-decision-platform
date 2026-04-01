from ads_platform.pacing.controllers import BoundedProportionalController
from ads_platform.schemas.pacing import BudgetState


def test_bounded_controller_clips_output() -> None:
    controller = BoundedProportionalController(kp=10.0, min_multiplier=0.5, max_multiplier=1.5)
    state = BudgetState(
        entity_id="cmp_1",
        date="2026-04-01",
        budget_amount=100.0,
        spend_so_far=0.0,
        target_spend_so_far=100.0,
        pacing_multiplier=1.0,
        throttle_prob=1.0,
        shadow_lambda=None,
        last_update_ts_ms=0,
        stale=False,
    )
    directive = controller.update(state)
    assert directive.pacing_multiplier == 1.5
