from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DecisionLog(BaseModel):
    request_id: str
    ad_id: str
    campaign_id: str
    model_version: str
    calibration_version: str
    landscape_version: str
    pctr_raw: float
    pctr_calibrated: float
    bid_base: float
    bid_effective: float
    throttle_prob: float
    pacing_multiplier: float
    shadow_lambda: float | None = None
    estimated_win_prob: float | None = None
    estimated_cost: float | None = None
    rank_score: float
    selected: bool
    slot: int | None = None
    timestamp_ms: int
    debug: dict[str, Any] = Field(default_factory=dict)
