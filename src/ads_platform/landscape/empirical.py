from __future__ import annotations

from dataclasses import dataclass

from ads_platform.common.utils import clip
from ads_platform.landscape.base import BidLandscapeModel
from ads_platform.schemas.landscape import LandscapeContext, LandscapeEstimate


@dataclass
class SegmentCurve:
    slope: float
    midpoint: float
    cost_fraction: float


class EmpiricalLandscapeModel(BidLandscapeModel):
    """Simple parametric approximation for starter integration.

    In production this can be replaced by a piecewise or HDMI-style estimator.
    """

    def __init__(
        self,
        curves_by_segment: dict[int | None, SegmentCurve],
        default_curve: SegmentCurve,
        model_version: str = "empirical_v0",
    ):
        self.curves_by_segment = curves_by_segment
        self.default_curve = default_curve
        self.model_version = model_version

    def _curve_for(self, context: LandscapeContext) -> SegmentCurve:
        return self.curves_by_segment.get(context.segment_id, self.default_curve)

    def estimate(self, bid: float, context: LandscapeContext) -> LandscapeEstimate:
        curve = self._curve_for(context)
        centered = curve.slope * (bid - curve.midpoint)
        win_prob = 1.0 / (1.0 + pow(2.718281828, -centered))
        win_prob = clip(win_prob, 0.0, 1.0)
        expected_cost = max(0.0, bid * curve.cost_fraction * win_prob)
        return LandscapeEstimate(
            win_prob=win_prob,
            expected_cost=expected_cost,
            expected_cpm=expected_cost * 1000.0,
            model_version=self.model_version,
            debug={
                "segment_id": context.segment_id,
                "slope": curve.slope,
                "midpoint": curve.midpoint,
                "cost_fraction": curve.cost_fraction,
            },
        )

    def optimal_bid(
        self,
        context: LandscapeContext,
        value_per_click: float,
        bid_cap: float | None = None,
    ) -> float:
        bid = max(0.0, value_per_click)
        if bid_cap is not None:
            bid = min(bid, bid_cap)
        return bid
