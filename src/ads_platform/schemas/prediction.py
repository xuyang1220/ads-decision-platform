from dataclasses import dataclass
from typing import Optional
from request import RequestContext, AdCandidate
from features import FeatureTransformer
from abc import ABC, abstractmethod


@dataclass
class PredictionResult:
    pctr_raw: float
    pctr_calibrated: float
    pcvr_raw: Optional[float] = None
    pcvr_calibrated: Optional[float] = None
    model_version: str = ""
    calibration_version: str = ""
    debug: dict | None = None


class CTRPredictor(ABC):
    @abstractmethod
    def predict(
        self,
        request: RequestContext,
        candidate: AdCandidate,
    ) -> PredictionResult:
        raise NotImplementedError
    

class DeepFMPredictor(CTRPredictor):
    def __init__(self, model, transformer: FeatureTransformer, calibrator):
        self.model = model
        self.transformer = transformer
        self.calibrator = calibrator

    def predict(
        self,
        request: RequestContext,
        candidate: AdCandidate,
    ) -> PredictionResult:
        x = self.transformer.transform(request, candidate)
        raw = float(self.model.predict(x))
        calibrated = float(self.calibrator.transform(raw))
        return PredictionResult(
            pctr_raw=raw,
            pctr_calibrated=calibrated,
            model_version="deepfm_v1",
            calibration_version="iso_v1",
        )
    
class ProbabilityCalibrator(ABC):
    @abstractmethod
    def transform(self, p: float) -> float:
        raise NotImplementedError


class IdentityCalibrator(ProbabilityCalibrator):
    def transform(self, p: float) -> float:
        return max(0.0, min(1.0, p))