from typing import Optional, Dict, Any

@dataclass
class LandscapeContext:
    campaign_id: str
    adgroup_id: str
    segment_id: Optional[int]
    channel: str
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LandscapeEstimate:
    win_prob: float
    expected_cost: float
    expected_cpm: Optional[float] = None
    expected_value: Optional[float] = None
    model_version: str = ""
    debug: dict | None = None


class BidLandscapeModel(ABC):
    @abstractmethod
    def estimate(
        self,
        bid: float,
        context: LandscapeContext,
    ) -> LandscapeEstimate:
        raise NotImplementedError

    @abstractmethod
    def optimal_bid(
        self,
        context: LandscapeContext,
        value_per_click: float,
        bid_cap: Optional[float] = None,
    ) -> float:
        raise NotImplementedError