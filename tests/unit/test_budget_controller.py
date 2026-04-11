from ads_platform.pacing.controllers import BoundedProportionalController
from ads_platform.pacing.desired_curve import FrontLoadedSpendCurve, UniformSpendCurve
from ads_platform.schemas.pacing import BudgetState


def test_bounded_proportional_controller_reduces_multiplier_when_overspending():
    controller = BoundedProportionalController(kp=2.0)
    state = BudgetState(
        entity_id="camp",
        date="2026-04-07",
        budget_amount=100.0,
        spend_so_far=80.0,
        target_spend_so_far=60.0,
        pacing_multiplier=1.0,
        throttle_prob=1.0,
        last_update_ts_ms=0,
    )
    directive = controller.update(state)
    assert directive.pacing_multiplier < 1.0


def test_bounded_proportional_controller_increases_multiplier_when_underspending():
    controller = BoundedProportionalController(kp=2.0)
    state = BudgetState(
        entity_id="camp",
        date="2026-04-07",
        budget_amount=100.0,
        spend_so_far=20.0,
        target_spend_so_far=60.0,
        pacing_multiplier=1.0,
        throttle_prob=1.0,
        last_update_ts_ms=0,
    )
    directive = controller.update(state)
    assert directive.pacing_multiplier > 1.0


def test_spend_curves_are_monotone_and_finish_near_one():
    uniform = UniformSpendCurve()
    front = FrontLoadedSpendCurve()
    assert uniform.target_fraction(0) <= uniform.target_fraction(720) <= uniform.target_fraction(1440)
    assert front.target_fraction(0) <= front.target_fraction(720) <= front.target_fraction(1440)
    assert abs(uniform.target_fraction(1440) - 1.0) < 1e-12
    assert abs(front.target_fraction(1440) - 1.0) < 1e-12
