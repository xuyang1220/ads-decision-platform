from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ads_platform.common.utils import clip
from ads_platform.landscape.base import BidLandscapeModel
from ads_platform.landscape.fallback import candidate_fallback_keys
from ads_platform.schemas.landscape import LandscapeContext, LandscapeEstimate


@dataclass(slots=True)
class SegmentCurve:
    slope: float
    midpoint: float
    cost_fraction: float


@dataclass(slots=True)
class EmpiricalTable:
    bids: list[float]
    win_probs: list[float]
    expected_costs: list[float]

    def __post_init__(self) -> None:
        if not (self.bids and self.win_probs and self.expected_costs):
            raise ValueError("EmpiricalTable requires non-empty bids, win_probs, and expected_costs")
        if not (len(self.bids) == len(self.win_probs) == len(self.expected_costs)):
            raise ValueError("EmpiricalTable arrays must have identical length")
        self.bids = [float(x) for x in self.bids]
        self.win_probs = _make_monotone(self.win_probs)
        self.expected_costs = _make_monotone(self.expected_costs)


def _make_monotone(values: Iterable[float]) -> list[float]:
    monotone: list[float] = []
    running = float("-inf")
    for value in values:
        running = max(running, float(value))
        monotone.append(running)
    return monotone


def interpolate_monotone(x: float, xs: list[float], ys: list[float]) -> float:
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(1, len(xs)):
        left_x, right_x = xs[i - 1], xs[i]
        if x <= right_x:
            left_y, right_y = ys[i - 1], ys[i]
            if right_x == left_x:
                return right_y
            weight = (x - left_x) / (right_x - left_x)
            return left_y + weight * (right_y - left_y)
    return ys[-1]


class EmpiricalLandscapeModel(BidLandscapeModel):
    """Production-shaped starter empirical bid landscape.

    Supports either:
    1. fallback tables keyed by adgroup/campaign/channel/global levels, or
    2. legacy segment curves for simple demos.
    """

    def __init__(
        self,
        tables_by_key: dict[str, EmpiricalTable] | None = None,
        curves_by_segment: dict[int | None, SegmentCurve] | None = None,
        default_curve: SegmentCurve | None = None,
        model_version: str = "empirical_v1",
    ):
        if not tables_by_key and default_curve is None:
            raise ValueError("Either tables_by_key or default_curve must be provided")
        self.tables_by_key = tables_by_key or {}
        self.curves_by_segment = curves_by_segment or {}
        self.default_curve = default_curve
        self.model_version = model_version

    def _resolve_table(self, context: LandscapeContext) -> tuple[EmpiricalTable | None, str]:
        for level, key in candidate_fallback_keys(context):
            if key in self.tables_by_key:
                return self.tables_by_key[key], level
        return None, "curve_fallback"

    def _curve_for(self, context: LandscapeContext) -> SegmentCurve:
        if context.segment_id in self.curves_by_segment:
            return self.curves_by_segment[context.segment_id]
        if None in self.curves_by_segment:
            return self.curves_by_segment[None]
        if self.default_curve is None:
            raise ValueError("No default curve configured")
        return self.default_curve

    def estimate(self, bid: float, context: LandscapeContext) -> LandscapeEstimate:
        bid = max(0.0, float(bid))
        table, fallback_level = self._resolve_table(context)
        if table is not None:
            win_prob = clip(interpolate_monotone(bid, table.bids, table.win_probs), 0.0, 1.0)
            expected_cost = max(0.0, interpolate_monotone(bid, table.bids, table.expected_costs))
            return LandscapeEstimate(
                win_prob=win_prob,
                expected_cost=expected_cost,
                expected_cpm=expected_cost * 1000.0,
                model_version=self.model_version,
                debug={
                    "fallback_level": fallback_level,
                    "table_key_resolved": True,
                    "bid": bid,
                },
            )

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
                "fallback_level": fallback_level,
                "segment_id": context.segment_id,
                "slope": curve.slope,
                "midpoint": curve.midpoint,
                "cost_fraction": curve.cost_fraction,
                "bid": bid,
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
