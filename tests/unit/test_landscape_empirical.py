from ads_platform.landscape.empirical import EmpiricalLandscapeModel, EmpiricalTable, SegmentCurve
from ads_platform.schemas.landscape import LandscapeContext


def test_empirical_landscape_monotone_in_bid():
    model = EmpiricalLandscapeModel(
        tables_by_key={
            "global": EmpiricalTable(
                bids=[0.1, 1.0, 2.0],
                win_probs=[0.05, 0.2, 0.5],
                expected_costs=[0.02, 0.15, 0.4],
            )
        },
        default_curve=SegmentCurve(slope=1.0, midpoint=1.0, cost_fraction=0.6),
    )
    context = LandscapeContext(campaign_id="camp", adgroup_id="ag", segment_id=None, channel="feed")
    low = model.estimate(0.5, context)
    high = model.estimate(1.5, context)
    assert high.win_prob >= low.win_prob
    assert high.expected_cost >= low.expected_cost


def test_empirical_landscape_falls_back_to_global_table():
    model = EmpiricalLandscapeModel(
        tables_by_key={
            "global": EmpiricalTable(
                bids=[0.1, 1.0, 2.0],
                win_probs=[0.05, 0.2, 0.5],
                expected_costs=[0.02, 0.15, 0.4],
            )
        },
        default_curve=SegmentCurve(slope=1.0, midpoint=1.0, cost_fraction=0.6),
    )
    context = LandscapeContext(campaign_id="camp", adgroup_id="ag", segment_id=9, channel="feed")
    estimate = model.estimate(1.0, context)
    assert estimate.debug["fallback_level"] == "global"
