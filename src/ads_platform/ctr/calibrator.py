from __future__ import annotations

from ads_platform.common.utils import clip
from ads_platform.ctr.base import ProbabilityCalibrator


class IdentityCalibrator(ProbabilityCalibrator):
    def transform(self, p: float) -> float:
        return clip(p, 0.0, 1.0)


class AffineCalibrator(ProbabilityCalibrator):
    """Simple placeholder calibrator.

    Useful for bootstrapping integration before plugging in isotonic or Platt scaling.
    """

    def __init__(self, scale: float = 1.0, bias: float = 0.0):
        self.scale = scale
        self.bias = bias

    def transform(self, p: float) -> float:
        return clip(self.scale * p + self.bias, 0.0, 1.0)
