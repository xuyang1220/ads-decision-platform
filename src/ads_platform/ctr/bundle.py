from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch

from ads_platform.ctr.calibrator import AffineCalibrator, IdentityCalibrator
from ads_platform.ctr.deepfm_model import DeepFMNetwork, TorchInferenceWrapper
from ads_platform.ctr.feature_spec import DeepFMFeatureSpec
from ads_platform.ctr.predictor import DeepFMPredictor
from ads_platform.ctr.transformers import DeepFMFeatureTransformer


@dataclass(slots=True)
class CTRBundle:
    predictor: DeepFMPredictor
    manifest: dict[str, Any]


class CTRBundleLoader:
    @staticmethod
    def _load_calibrator(payload: dict[str, Any]):
        kind = payload.get("type", "identity")
        if kind == "identity":
            return IdentityCalibrator()
        if kind == "affine":
            return AffineCalibrator(scale=float(payload.get("scale", 1.0)), bias=float(payload.get("bias", 0.0)))
        raise ValueError(f"Unsupported calibrator type: {kind}")

    @classmethod
    def load(cls, bundle_dir: str | Path, device: str = "cpu") -> CTRBundle:
        bundle_path = Path(bundle_dir)
        manifest = json.loads((bundle_path / "manifest.json").read_text())
        feature_spec = DeepFMFeatureSpec.from_dict(json.loads((bundle_path / manifest["feature_spec"]).read_text()))
        model_config = manifest["model_config"]
        model = DeepFMNetwork(
            field_bucket_sizes=model_config["field_bucket_sizes"],
            num_dense_features=model_config["num_dense_features"],
            embedding_dim=model_config.get("embedding_dim", 8),
            mlp_hidden_dims=tuple(model_config.get("mlp_hidden_dims", [64, 32])),
        )
        state_dict = torch.load(bundle_path / manifest["weights"], map_location=device)
        model.load_state_dict(state_dict)

        predictor = DeepFMPredictor(
            model=TorchInferenceWrapper(model=model, device=device),
            transformer=DeepFMFeatureTransformer(feature_spec),
            calibrator=cls._load_calibrator(manifest.get("calibrator", {"type": "identity"})),
            model_version=manifest.get("model_version", "deepfm_bundle_v0"),
            calibration_version=manifest.get("calibration_version", manifest.get("calibrator", {}).get("type", "identity")),
        )
        return CTRBundle(predictor=predictor, manifest=manifest)
