from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RequestContext:
    request_id: str
    timestamp_ms: int
    user_id: Optional[str]
    device_type: str
    country: str
    placement: str
    app_or_site: str
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AdCandidate:
    ad_id: str
    campaign_id: str
    adgroup_id: str
    advertiser_id: Optional[str]
    base_bid: float
    features: Dict[str, Any] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuctionInput:
    request: RequestContext
    candidates: List[AdCandidate]