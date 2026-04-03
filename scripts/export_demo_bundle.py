from __future__ import annotations

import json
from pathlib import Path

import torch

from ads_platform.ctr.deepfm_model import DeepFMNetwork
from ads_platform.ctr.feature_spec import CategoricalFeatureSpec, DeepFMFeatureSpec, NumericFeatureSpec


def main() -> None:
    out_dir = Path("artifacts/demo_bundle")
    out_dir.mkdir(parents=True, exist_ok=True)

    feature_spec = DeepFMFeatureSpec(
        numeric_features=[
            NumericFeatureSpec(name="base_bid", default=0.0, log1p=True),
            NumericFeatureSpec(name="historical_ctr", default=0.0, log1p=False),
        ],
        categorical_features=[
            CategoricalFeatureSpec(name="device_type", num_buckets=64),
            CategoricalFeatureSpec(name="country", num_buckets=64),
            CategoricalFeatureSpec(name="placement", num_buckets=32),
            CategoricalFeatureSpec(name="campaign_id", num_buckets=128),
        ],
    )

    model = DeepFMNetwork(
        field_bucket_sizes=[64, 64, 32, 128],
        num_dense_features=2,
        embedding_dim=4,
        mlp_hidden_dims=(16, 8),
    )

    torch.manual_seed(7)
    for param in model.parameters():
        if param.ndim > 1:
            torch.nn.init.xavier_uniform_(param)
        else:
            torch.nn.init.zeros_(param)

    torch.save(model.state_dict(), out_dir / "deepfm_demo.pt")
    (out_dir / "feature_spec.json").write_text(json.dumps(feature_spec.to_dict(), indent=2))
    manifest = {
        "model_version": "deepfm_demo_v1",
        "calibration_version": "affine_demo_v1",
        "feature_spec": "feature_spec.json",
        "weights": "deepfm_demo.pt",
        "model_config": {
            "field_bucket_sizes": [64, 64, 32, 128],
            "num_dense_features": 2,
            "embedding_dim": 4,
            "mlp_hidden_dims": [16, 8],
        },
        "calibrator": {"type": "affine", "scale": 0.9, "bias": 0.01},
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Wrote demo bundle to {out_dir}")


if __name__ == "__main__":
    main()
