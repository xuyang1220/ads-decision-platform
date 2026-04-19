from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
from typing import Any

from ads_platform.landscape.empirical import EmpiricalLandscapeModel, EmpiricalTable, SegmentCurve


@dataclass(slots=True)
class EmpiricalLandscapeArtifact:
    model_version: str
    tables_by_key: dict[str, EmpiricalTable]
    curves_by_segment: dict[int | None, SegmentCurve] | None = None
    default_curve: SegmentCurve | None = None
    metadata: dict[str, Any] | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "artifact_type": "empirical_landscape",
            "model_version": self.model_version,
            "metadata": self.metadata or {},
            "tables_by_key": {
                key: {
                    "bids": table.bids,
                    "win_probs": table.win_probs,
                    "expected_costs": table.expected_costs,
                }
                for key, table in self.tables_by_key.items()
            },
            "curves_by_segment": {
                ("null" if key is None else str(key)): {
                    "slope": curve.slope,
                    "midpoint": curve.midpoint,
                    "cost_fraction": curve.cost_fraction,
                }
                for key, curve in (self.curves_by_segment or {}).items()
            },
            "default_curve": (
                None
                if self.default_curve is None
                else {
                    "slope": self.default_curve.slope,
                    "midpoint": self.default_curve.midpoint,
                    "cost_fraction": self.default_curve.cost_fraction,
                }
            ),
        }

    def write_json(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with Path(path).open("w", encoding="utf-8") as handle:
            json.dump(self.to_payload(), handle, indent=2)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "EmpiricalLandscapeArtifact":
        if payload.get("artifact_type") not in (None, "empirical_landscape"):
            raise ValueError(f"Unsupported artifact_type={payload.get('artifact_type')!r}")
        tables_by_key = {
            str(key): EmpiricalTable(
                bids=list(value["bids"]),
                win_probs=list(value["win_probs"]),
                expected_costs=list(value["expected_costs"]),
            )
            for key, value in dict(payload.get("tables_by_key", {})).items()
        }
        curves_raw = dict(payload.get("curves_by_segment", {}))
        curves_by_segment: dict[int | None, SegmentCurve] = {}
        for key, value in curves_raw.items():
            parsed_key = None if key in ("null", "None", None) else int(key)
            curves_by_segment[parsed_key] = SegmentCurve(
                slope=float(value["slope"]),
                midpoint=float(value["midpoint"]),
                cost_fraction=float(value["cost_fraction"]),
            )
        default_curve_payload = payload.get("default_curve")
        default_curve = None
        if default_curve_payload is not None:
            default_curve = SegmentCurve(
                slope=float(default_curve_payload["slope"]),
                midpoint=float(default_curve_payload["midpoint"]),
                cost_fraction=float(default_curve_payload["cost_fraction"]),
            )
        return cls(
            model_version=str(payload.get("model_version", "empirical_v1")),
            tables_by_key=tables_by_key,
            curves_by_segment=curves_by_segment or None,
            default_curve=default_curve,
            metadata=dict(payload.get("metadata", {})),
        )

    @classmethod
    def read_json(cls, path: str | Path) -> "EmpiricalLandscapeArtifact":
        with Path(path).open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return cls.from_payload(payload)

    def build_model(self) -> EmpiricalLandscapeModel:
        return EmpiricalLandscapeModel(
            tables_by_key=self.tables_by_key,
            curves_by_segment=self.curves_by_segment,
            default_curve=self.default_curve,
            model_version=self.model_version,
        )
