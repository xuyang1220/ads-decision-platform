from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ads_platform.schemas.landscape import LandscapeEstimate
from ads_platform.schemas.prediction import PredictionResult
from ads_platform.schemas.request import AdCandidate


class ScoredCandidate(BaseModel):
    candidate: AdCandidate
    prediction: PredictionResult
    bid: float
    throttle_prob: float
    rank_score: float
    landscape: LandscapeEstimate | None = None
    debug: dict[str, Any] = Field(default_factory=dict)


class AuctionResult(BaseModel):
    request_id: str
    winners: list[ScoredCandidate]
    dropped: list[ScoredCandidate]
    debug: dict[str, Any] = Field(default_factory=dict)
