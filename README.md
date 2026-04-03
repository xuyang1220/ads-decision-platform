# ads_decision_platform

Starter codebase for a production-oriented ads decision platform with:

- DeepFM-style CTR prediction interface
- probability calibration
- bid landscape estimation
- budget pacing directives
- ranking and multi-slot allocation
- decision logging
- integration test for end-to-end auction flow

## Quick start

```bash
cd ads_decision_platform
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest -q
```

## Package layout

- `schemas/`: typed request, prediction, pacing, ranking, and log contracts
- `ctr/`: predictor, calibrator, dummy model, artifact loader placeholder
- `landscape/`: landscape model interfaces and a simple empirical implementation
- `pacing/`: budget state and a bounded proportional controller
- `ranking/`: scoring and multi-slot allocation
- `decisioning/`: the vertical-slice decision engine
- `serving/`: small FastAPI example service

## What is intentionally simplified

This starter keeps persistence, distributed serving, feature stores, and real model serialization minimal so you can swap in your own implementations incrementally.


## Criteo training + historical replay wiring

This repo now includes two concrete adapters:

- `scripts/train_criteo_deepfm.py` trains a real PyTorch DeepFM bundle directly from the classic Criteo `train.txt` format (`label`, `I1..I13`, `C1..C26`, tab-separated, no header).
- `scripts/run_historical_replay.py` loads JSONL historical auction logs and replays them through the bundle + decision engine.

### Train on Criteo

```bash
python scripts/train_criteo_deepfm.py   --train-path ../data/criteo/train.txt   --output-dir artifacts/criteo_bundle   --max-rows 5000000   --batch-size 4096   --epochs 1   --embedding-dim 16
```

The training path uses an offset-based dataset so it does not materialize the full file into memory.

### Historical replay log format

Supported JSONL auction shape:

```json
{
  "record_id": "auction-1",
  "request": {
    "request_id": "req-1",
    "timestamp_ms": 1712000000000,
    "device_type": "mobile",
    "country": "US",
    "placement": "feed",
    "app_or_site": "example.com",
    "extra": {"hour": 12}
  },
  "num_slots": 2,
  "candidates": [
    {
      "ad_id": "ad-1",
      "campaign_id": "camp-1",
      "adgroup_id": "ag-1",
      "base_bid": 1.2,
      "features": {"I1": "3", "C1": "abcd", "device_type": "mobile"},
      "clicked": 1,
      "realized_spend": 0.61
    }
  ],
  "observed": {
    "clicked_ad_ids": ["ad-1"],
    "spend_by_ad_id": {"ad-1": 0.61}
  }
}
```

### Run replay

```bash
python scripts/run_historical_replay.py   --bundle-dir artifacts/criteo_bundle   --logs-path data/historical_auctions.jsonl   --default-num-slots 2
```
