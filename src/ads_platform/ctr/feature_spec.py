from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class NumericFeatureSpec:
    name: str
    default: float = 0.0
    log1p: bool = False


@dataclass(slots=True)
class CategoricalFeatureSpec:
    name: str
    num_buckets: int
    default_token: str = "__MISSING__"


@dataclass(slots=True)
class DeepFMFeatureSpec:
    numeric_features: list[NumericFeatureSpec] = field(default_factory=list)
    categorical_features: list[CategoricalFeatureSpec] = field(default_factory=list)

    @property
    def total_fields(self) -> int:
        return len(self.numeric_features) + len(self.categorical_features)

    def numeric_defaults(self) -> dict[str, float]:
        return {feature.name: feature.default for feature in self.numeric_features}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DeepFMFeatureSpec":
        return cls(
            numeric_features=[NumericFeatureSpec(**row) for row in payload.get("numeric_features", [])],
            categorical_features=[CategoricalFeatureSpec(**row) for row in payload.get("categorical_features", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "numeric_features": [asdict(feature) for feature in self.numeric_features],
            "categorical_features": [asdict(feature) for feature in self.categorical_features],
        }
