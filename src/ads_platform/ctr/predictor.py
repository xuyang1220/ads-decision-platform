from __future__ import annotations

from dataclasses import dataclass
from hashlib import md5
import math
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




def _stable_uniform(seed: str) -> float:
    digest = md5(seed.encode("utf-8")).hexdigest()
    return (int(digest[:8], 16) + 0.5) / (0xFFFFFFFF + 1.0)


def _stable_normal(seed: str) -> float:
    u1 = max(_stable_uniform(seed + "|u1"), 1e-12)
    u2 = _stable_uniform(seed + "|u2")
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def _clip_probability(value: float, eps: float = 1e-6) -> float:
    return min(1.0 - eps, max(eps, value))


def _logit(p: float) -> float:
    p = _clip_probability(p)
    return math.log(p / (1.0 - p))


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _extract_oracle_pctr(candidate: AdCandidate) -> float:
    for container in (candidate.extra, candidate.features):
        if "oracle_pctr" in container:
            return _clip_probability(float(container["oracle_pctr"]))
        if "true_pctr" in container:
            return _clip_probability(float(container["true_pctr"]))
    raise ValueError(
        f"Oracle predictor requires candidate.extra['oracle_pctr'] or candidate.features['oracle_pctr'] for ad_id={candidate.ad_id}"
    )

class OracleCTRPredictor(CTRPredictor):
    def __init__(
        self,
        calibrator: ProbabilityCalibrator,
        model_version: str = "oracle_ctr_v1",
        calibration_version: str = "identity_v0",
    ):
        self.calibrator = calibrator
        self.model_version = model_version
        self.calibration_version = calibration_version

    def predict(self, request: RequestContext, candidate: AdCandidate) -> PredictionResult:
        raw = _extract_oracle_pctr(candidate)
        calibrated = float(self.calibrator.transform(raw))
        return PredictionResult(
            pctr_raw=raw,
            pctr_calibrated=calibrated,
            model_version=self.model_version,
            calibration_version=self.calibration_version,
            debug={"predictor": "oracle", "request_id": request.request_id},
        )


class NoisyOracleCTRPredictor(CTRPredictor):
    def __init__(
        self,
        calibrator: ProbabilityCalibrator,
        noise_sigma: float = 0.5,
        bias: float = 0.0,
        model_version: str = "noisy_oracle_ctr_v1",
        calibration_version: str = "identity_v0",
    ):
        self.calibrator = calibrator
        self.noise_sigma = noise_sigma
        self.bias = bias
        self.model_version = model_version
        self.calibration_version = calibration_version

    def predict(self, request: RequestContext, candidate: AdCandidate) -> PredictionResult:
        oracle = _extract_oracle_pctr(candidate)
        seed = f"{request.request_id}|{candidate.ad_id}|{candidate.campaign_id}"
        z = _stable_normal(seed)
        raw = _sigmoid(_logit(oracle) + self.bias + self.noise_sigma * z)
        calibrated = float(self.calibrator.transform(raw))
        return PredictionResult(
            pctr_raw=raw,
            pctr_calibrated=calibrated,
            model_version=self.model_version,
            calibration_version=self.calibration_version,
            debug={
                "predictor": "noisy_oracle",
                "oracle_pctr": oracle,
                "noise_sigma": self.noise_sigma,
                "bias": self.bias,
                "z": z,
            },
        )


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
