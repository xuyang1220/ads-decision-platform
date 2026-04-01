from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RequestContext(BaseModel):
    request_id: str
    timestamp_ms: int
    user_id: str | None = None
    device_type: str
    country: str
    placement: str
    app_or_site: str
    extra: dict[str, Any] = Field(default_factory=dict)


class AdCandidate(BaseModel):
    ad_id: str
    campaign_id: str
    adgroup_id: str
    advertiser_id: str | None = None
    base_bid: float
    features: dict[str, Any] = Field(default_factory=dict)
    extra: dict[str, Any] = Field(default_factory=dict)


class AuctionInput(BaseModel):
    request: RequestContext
    candidates: list[AdCandidate]
