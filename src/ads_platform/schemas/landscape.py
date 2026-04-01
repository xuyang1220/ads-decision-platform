from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LandscapeContext(BaseModel):
    campaign_id: str
    adgroup_id: str
    segment_id: int | None = None
    channel: str
    extra: dict[str, Any] = Field(default_factory=dict)


class LandscapeEstimate(BaseModel):
    win_prob: float
    expected_cost: float
    expected_cpm: float | None = None
    expected_value: float | None = None
    model_version: str = ""
    debug: dict[str, Any] = Field(default_factory=dict)
