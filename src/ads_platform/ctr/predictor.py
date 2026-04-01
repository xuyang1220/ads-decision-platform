from __future__ import annotations

from dataclasses import dataclass
from hashlib import md5
from typing import Any

from ads_platform.ctr.base import CTRPredictor, FeatureTransformer, ProbabilityCalibrator
from ads_platform.schemas.prediction import PredictionResult
from ads_platform.schemas.request import AdCandidate, RequestContext


class DictFeatureTransformer(FeatureTransformer):
    """Minimal deterministic transformer.

    Replace this with the exact production DeepFM feature logic later.
    """

    def transform(self, request: RequestContext, candidate: AdCandidate) -> dict[str, Any]:
        return {
            "device_type": request.device_type,
            "country": request.country,
            "placement": request.placement,
            "base_bid": candidate.base_bid,
            **candidate.features,
        }


@dataclass
class DummyCTRModel:
    """Deterministic pseudo-model for integration testing.

    The model returns a stable probability derived from a hashed feature payload.
    """

    salt: str = "ctr_v0"

    def predict(self, features: dict[str, Any]) -> float:
        payload = "|".join(f"{k}={features[k]}" for k in sorted(features)) + f"|{self.salt}"
        digest = md5(payload.encode("utf-8")).hexdigest()
        raw = int(digest[:8], 16) / 0xFFFFFFFF
        return 0.01 + 0.25 * raw


class DeepFMPredictor(CTRPredictor):
    def __init__(
        self,
        model: Any,
        transformer: FeatureTransformer,
        calibrator: ProbabilityCalibrator,
        model_version: str = "deepfm_v0",
        calibration_version: str = "identity_v0",
    ):
        self.model = model
        self.transformer = transformer
        self.calibrator = calibrator
        self.model_version = model_version
        self.calibration_version = calibration_version

    def predict(self, request: RequestContext, candidate: AdCandidate) -> PredictionResult:
        x = self.transformer.transform(request, candidate)
        raw = float(self.model.predict(x))
        calibrated = float(self.calibrator.transform(raw))
        return PredictionResult(
            pctr_raw=raw,
            pctr_calibrated=calibrated,
            model_version=self.model_version,
            calibration_version=self.calibration_version,
            debug={"feature_keys": sorted(x.keys())},
        )
