from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from ads_platform.schemas.prediction import PredictionResult
from ads_platform.schemas.request import AdCandidate, RequestContext


class FeatureTransformer(ABC):
    @abstractmethod
    def transform(
        self,
        request: RequestContext,
        candidate: AdCandidate,
    ) -> Mapping[str, Any]:
        raise NotImplementedError


class ProbabilityCalibrator(ABC):
    @abstractmethod
    def transform(self, p: float) -> float:
        raise NotImplementedError


class CTRPredictor(ABC):
    @abstractmethod
    def predict(
        self,
        request: RequestContext,
        candidate: AdCandidate,
    ) -> PredictionResult:
        raise NotImplementedError
