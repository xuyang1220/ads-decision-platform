from ads_platform.landscape.empirical import EmpiricalLandscapeModel, SegmentCurve
from ads_platform.schemas.landscape import LandscapeContext


def test_win_prob_increases_with_bid() -> None:
    model = EmpiricalLandscapeModel(
        curves_by_segment={},
        default_curve=SegmentCurve(slope=2.0, midpoint=1.0, cost_fraction=0.7),
    )
    context = LandscapeContext(campaign_id="cmp", adgroup_id="ag", segment_id=None, channel="feed")
    low = model.estimate(0.5, context)
    high = model.estimate(1.5, context)
    assert high.win_prob > low.win_prob
    assert high.expected_cost >= low.expected_cost
