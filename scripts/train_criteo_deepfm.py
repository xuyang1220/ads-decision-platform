from __future__ import annotations

import argparse
import json

from ads_platform.ctr.trainer import CriteoDeepFMTrainer, DeepFMTrainConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="Train DeepFM on the Criteo tab-separated train.txt file")
    parser.add_argument("--train-path", required=True, help="Path to Criteo train.txt")
    parser.add_argument("--output-dir", required=True, help="Directory for exported bundle artifacts")
    parser.add_argument("--max-rows", type=int, default=None, help="Optional row cap for quick experiments")
    parser.add_argument("--validation-fraction", type=float, default=0.1)
    parser.add_argument("--batch-size", type=int, default=4096)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--embedding-dim", type=int, default=16)
    parser.add_argument("--bucket-size-per-field", type=int, default=65536)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    config = DeepFMTrainConfig(
        train_path=args.train_path,
        output_dir=args.output_dir,
        max_rows=args.max_rows,
        validation_fraction=args.validation_fraction,
        batch_size=args.batch_size,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        embedding_dim=args.embedding_dim,
        bucket_size_per_field=args.bucket_size_per_field,
        device=args.device,
    )
    result = CriteoDeepFMTrainer(config).fit()
    print(json.dumps(result.manifest, indent=2))


if __name__ == "__main__":
    main()
