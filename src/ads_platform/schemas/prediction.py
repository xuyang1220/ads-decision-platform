from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PredictionResult(BaseModel):
    pctr_raw: float
    pctr_calibrated: float
    pcvr_raw: float | None = None
    pcvr_calibrated: float | None = None
    model_version: str = ""
    calibration_version: str = ""
    debug: dict[str, Any] = Field(default_factory=dict)
