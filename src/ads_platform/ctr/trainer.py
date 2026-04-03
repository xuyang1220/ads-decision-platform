from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader

from ads_platform.ctr.deepfm_model import DeepFMNetwork
from ads_platform.ctr.feature_spec import DeepFMFeatureSpec
from ads_platform.data.criteo import CriteoOffsetDataset, default_criteo_feature_spec
from dataclasses import asdict


@dataclass(slots=True)
class DeepFMTrainConfig:
    train_path: str
    output_dir: str
    max_rows: int | None = None
    validation_fraction: float = 0.1
    batch_size: int = 4096
    num_workers: int = 0
    epochs: int = 1
    learning_rate: float = 1e-3
    embedding_dim: int = 16
    mlp_hidden_dims: tuple[int, ...] = (128, 64)
    bucket_size_per_field: int = 65536
    device: str = "cpu"
    seed: int = 42


@dataclass(slots=True)
class TrainEpochMetrics:
    epoch: int
    train_loss: float
    val_loss: float


@dataclass(slots=True)
class TrainResult:
    bundle_dir: str
    metrics: list[TrainEpochMetrics]
    manifest: dict


class CriteoDeepFMTrainer:
    def __init__(self, config: DeepFMTrainConfig):
        self.config = config
        self.feature_spec: DeepFMFeatureSpec = default_criteo_feature_spec(config.bucket_size_per_field)
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _make_datasets(self) -> tuple[CriteoOffsetDataset, CriteoOffsetDataset]:
        full_dataset = CriteoOffsetDataset(
            data_path=self.config.train_path,
            feature_spec=self.feature_spec,
            max_rows=self.config.max_rows,
        )
        total = len(full_dataset)
        val_size = max(1, int(total * self.config.validation_fraction)) if total > 1 else 0
        train_size = max(1, total - val_size) if total else 0
        train_dataset = CriteoOffsetDataset(
            data_path=self.config.train_path,
            feature_spec=self.feature_spec,
            max_rows=self.config.max_rows,
            start_row=0,
            end_row=train_size,
        )
        val_dataset = CriteoOffsetDataset(
            data_path=self.config.train_path,
            feature_spec=self.feature_spec,
            max_rows=self.config.max_rows,
            start_row=train_size,
            end_row=train_size + val_size,
        )
        return train_dataset, val_dataset

    def fit(self) -> TrainResult:
        torch.manual_seed(self.config.seed)
        train_dataset, val_dataset = self._make_datasets()

        train_loader = DataLoader(
            train_dataset,
            batch_size=self.config.batch_size,
            shuffle=True,
            num_workers=self.config.num_workers,
        )
        val_loader = DataLoader(
            val_dataset,
            batch_size=self.config.batch_size,
            shuffle=False,
            num_workers=self.config.num_workers,
        )

        model = DeepFMNetwork(
            field_bucket_sizes=[f.num_buckets for f in self.feature_spec.categorical_features],
            num_dense_features=len(self.feature_spec.numeric_features),
            embedding_dim=self.config.embedding_dim,
            mlp_hidden_dims=self.config.mlp_hidden_dims,
        ).to(self.config.device)
        optimizer = torch.optim.Adam(model.parameters(), lr=self.config.learning_rate)
        loss_fn = nn.BCELoss()
        metrics: list[TrainEpochMetrics] = []

        for epoch in range(1, self.config.epochs + 1):
            model.train()
            train_loss_sum = 0.0
            train_examples = 0
            for batch in train_loader:
                dense_x = batch["dense_x"].to(self.config.device)
                sparse_x = batch["sparse_x"].to(self.config.device)
                labels = batch["label"].to(self.config.device)
                preds = model(dense_x, sparse_x)
                loss = loss_fn(preds, labels)
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                batch_size = labels.shape[0]
                train_loss_sum += float(loss.item()) * batch_size
                train_examples += batch_size

            model.eval()
            val_loss_sum = 0.0
            val_examples = 0
            with torch.no_grad():
                for batch in val_loader:
                    dense_x = batch["dense_x"].to(self.config.device)
                    sparse_x = batch["sparse_x"].to(self.config.device)
                    labels = batch["label"].to(self.config.device)
                    preds = model(dense_x, sparse_x)
                    loss = loss_fn(preds, labels)
                    batch_size = labels.shape[0]
                    val_loss_sum += float(loss.item()) * batch_size
                    val_examples += batch_size

            metrics.append(
                TrainEpochMetrics(
                    epoch=epoch,
                    train_loss=(train_loss_sum / max(train_examples, 1)),
                    val_loss=(val_loss_sum / max(val_examples, 1)),
                )
            )

        weights_name = "deepfm_criteo.pt"
        feature_spec_name = "feature_spec.json"
        manifest_name = "manifest.json"
        torch.save(model.state_dict(), self.output_dir / weights_name)
        (self.output_dir / feature_spec_name).write_text(json.dumps(self.feature_spec.to_dict(), indent=2))

        manifest = {
            "model_version": "deepfm_criteo_v1",
            "calibration_version": "identity",
            "weights": weights_name,
            "feature_spec": feature_spec_name,
            "model_config": {
                "field_bucket_sizes": [f.num_buckets for f in self.feature_spec.categorical_features],
                "num_dense_features": len(self.feature_spec.numeric_features),
                "embedding_dim": self.config.embedding_dim,
                "mlp_hidden_dims": list(self.config.mlp_hidden_dims),
            },
            "calibrator": {"type": "identity"},
            "training": {
                "train_path": self.config.train_path,
                "max_rows": self.config.max_rows,
                "epochs": self.config.epochs,
                "batch_size": self.config.batch_size,
                "learning_rate": self.config.learning_rate,
                "validation_fraction": self.config.validation_fraction,
                "metrics": [asdict(metric) for metric in metrics],
            },
        }
        (self.output_dir / manifest_name).write_text(json.dumps(manifest, indent=2))
        return TrainResult(bundle_dir=str(self.output_dir), metrics=metrics, manifest=manifest)
