from dataclasses import dataclass
from typing import Optional


@dataclass
class DecisionLog:
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
    shadow_lambda: Optional[float]
    estimated_win_prob: Optional[float]
    estimated_cost: Optional[float]
    rank_score: float
    selected: bool
    slot: Optional[int]
    timestamp_ms: int
    debug: dict | None = None