# Quickstart - Deploy in 5 Minutes

## Absolute Fastest Path (Docker Required)

```bash
# 1. Install Docker Desktop (if not installed)
#    macOS/Windows: https://www.docker.com/products/docker-desktop
#    Linux: sudo apt-get install docker.io docker-compose-plugin

# 2. Clone and navigate
git clone <repo-url>
cd ads-decision-platform

# 3. Start everything
docker-compose up -d --build

# 4. Test it works
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# 5. Make a decision request
curl -X POST http://localhost:8000/decide \
  -H "Content-Type: application/json" \
  -d '{
    "request": {
      "request_id": "quick_test",
      "timestamp_ms": 1609459200000,
      "device_type": "mobile",
      "country": "US",
      "placement": "feed",
      "app_or_site": "app_123"
    },
    "candidates": [{
      "ad_id": "ad_1",
      "campaign_id": "cmp_demo",
      "adgroup_id": "ag_1",
      "base_bid": 1.5,
      "features": {
        "I1": "5", "I2": "10", "I3": "15", "I4": "20", "I5": "25",
        "I6": "30", "I7": "35", "I8": "40", "I9": "45", "I10": "50",
        "I11": "55", "I12": "60", "I13": "65",
        "C1": "abc", "C2": "def", "C3": "ghi", "C4": "jkl", "C5": "mno",
        "C6": "pqr", "C7": "stu", "C8": "vwx", "C9": "yza", "C10": "bcd",
        "C11": "efg", "C12": "hij", "C13": "klm", "C14": "nop", "C15": "qrs",
        "C16": "tuv", "C17": "wxy", "C18": "zab", "C19": "cde", "C20": "fgh",
        "C21": "ijk", "C22": "lmn", "C23": "opq", "C24": "rst", "C25": "uvw",
        "C26": "xyz"
      }
    }]
  }'

# 6. View interactive docs
# Open http://localhost:8000/docs in your browser

# 7. Stop when done
docker-compose down
```

## If Docker Doesn't Work

```bash
# Install Python 3.10+
python3.10 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .[dev]

# Run server
uvicorn ads_platform.serving.api:app --reload

# Test (in another terminal)
curl http://localhost:8000/health
```

## Useful Commands

```bash
# View logs
docker-compose logs -f ads-api

# Restart after artifact changes
docker-compose restart

# Run tests
docker-compose run --rm ads-api pytest -v

# Open shell in container
docker exec -it ads-decision-api bash

# Stop everything
docker-compose down
```

## What's Running?

- **FastAPI server** on http://localhost:8000
- **CTR model**: DeepFM model (currently using DummyCTRModel, upgradeable to criteo_bundle)
- **Landscape model**: Empirical bid landscape (currently hard-coded, upgradeable to fitted)
- **Budget pacing**: In-memory budget state with demo campaigns

## Available Endpoints

- `GET  /health` - Health check
- `POST /decide` - Main decision endpoint (rank candidates + apply pacing)
- `GET  /docs` - Interactive API documentation (Swagger UI)
- `GET  /redoc` - Alternative API docs (ReDoc)

## Test With Interactive UI

1. Start the service: `docker-compose up -d --build`
2. Open browser: http://localhost:8000/docs
3. Click on `POST /decide` endpoint
4. Click "Try it out"
5. Modify the example JSON request
6. Click "Execute"
7. See the response below

## Next Steps

- **Full details**: See `DEPLOYMENT_GUIDE.md` for comprehensive instructions
- **Production setup**: See `DOCKER_DEPLOYMENT.md` for cloud deployment
- **Train models**: `python scripts/train_criteo_deepfm.py --help`
- **Run replays**: `python scripts/run_budget_replay.py --help`
- **Upgrade to production models**: Edit `src/ads_platform/serving/api.py` to load `criteo_bundle` and `fitted_landscape_oracle.json`

## Upgrading to Production Models

Current implementation uses dummy/hard-coded models. To use production artifacts:

**Edit `src/ads_platform/serving/api.py`:**

```python
# Replace lines 17-25 with:
from ads_platform.ctr.bundle import CTRBundleLoader
from ads_platform.landscape.loader import load_empirical_landscape

ctr_bundle = CTRBundleLoader.load("artifacts/criteo_bundle", device="cpu")
predictor = ctr_bundle.predictor

landscape = load_empirical_landscape("artifacts/fitted_landscape_oracle.json")
```

Then restart:
```bash
docker-compose restart
```

## Troubleshooting

**Port 8000 already in use?**
```bash
docker-compose down
# Edit docker-compose.yml: change "8000:8000" to "8001:8000"
docker-compose up -d
```

**Build fails?**
```bash
docker system prune -a
docker-compose build --no-cache
```

**Need more memory?**
```bash
# Edit docker-compose.yml, increase:
# deploy.resources.limits.memory: 8G
docker-compose restart
```

**Container crashes immediately?**
```bash
# Check logs
docker-compose logs ads-api

# Common issues:
# - Missing artifacts/ directory
# - Insufficient memory (increase Docker Desktop memory limit)
# - Port conflict (change port in docker-compose.yml)
```

**Artifacts not found?**
```bash
# Verify artifacts exist
ls -la artifacts/criteo_bundle/
ls -la artifacts/demo_bundle/
ls -la artifacts/fitted_landscape_oracle.json

# If missing, train new models:
python scripts/train_criteo_deepfm.py \
  --train-path data/criteo/train.txt \
  --output-dir artifacts/criteo_bundle \
  --max-rows 1000000
```

## Using Makefile Shortcuts

```bash
make help        # Show all available commands
make build       # Build Docker image
make up          # Start in detached mode
make up-build    # Build + start
make down        # Stop containers
make logs        # Follow logs
make shell       # Open bash in container
make health      # Check health endpoint
make test        # Run tests in container
make clean       # Remove everything (containers, images, volumes)
make restart     # Restart services
```

## Architecture Overview

```
Request Flow:
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ POST /decide
       ▼
┌─────────────────────────────────────┐
│        FastAPI Server               │
│    (src/ads_platform/serving/)      │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│      Decision Engine                │
│  (src/ads_platform/decisioning/)    │
├─────────────────────────────────────┤
│  1. CTR Prediction (DeepFM)         │
│  2. Landscape Estimation            │
│  3. Budget Pacing (multipliers)     │
│  4. Ranking & Multi-slot Allocation │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│    Response (JSON)                  │
│  - Ranked candidates                │
│  - Adjusted bids                    │
│  - Win probabilities                │
│  - Decision logs                    │
└─────────────────────────────────────┘
```

## Quick Performance Test

```bash
# Install apache bench (if not installed)
# macOS: brew install httpd
# Linux: sudo apt-get install apache2-utils

# Run 100 requests with 10 concurrent
ab -n 100 -c 10 -p request.json -T application/json http://localhost:8000/decide

# Or use wrk (more advanced)
# wrk -t2 -c10 -d30s -s post.lua http://localhost:8000/decide
```

## Development Workflow

```bash
# 1. Start with hot reload (local Python)
source .venv/bin/activate
uvicorn ads_platform.serving.api:app --reload

# 2. Make changes to src/ads_platform/serving/api.py

# 3. Server auto-reloads on save

# 4. Test changes
curl http://localhost:8000/health

# 5. Run tests
pytest tests/unit/test_api.py -v

# 6. When ready for Docker testing
docker-compose up --build
```

## Configuration via Environment Variables

Set in `docker-compose.yml` or pass to `docker run`:

```bash
# Example custom config
docker run -d \
  -e LOG_LEVEL=debug \
  -e CTR_BUNDLE_PATH=/app/artifacts/criteo_bundle \
  -e LANDSCAPE_PATH=/app/artifacts/fitted_landscape_oracle.json \
  -e INFERENCE_DEVICE=cpu \
  -p 8000:8000 \
  ads-decision-api:latest
```

## Monitoring (Optional)

Enable Prometheus + Grafana by uncommenting services in `docker-compose.yml`:

```bash
# Uncomment prometheus and grafana sections
vim docker-compose.yml

# Restart
docker-compose down
docker-compose up -d

# Access:
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
```

---

**You're now running a production-style ads decision platform! 🎉**

For more details, see:
- `DEPLOYMENT_GUIDE.md` - Comprehensive deployment guide
- `DOCKER_DEPLOYMENT.md` - Production deployment patterns
- `README.md` - Repository overview and architecture


Start-Process -Wait -FilePath ".\Docker Desktop Installer.exe" -ArgumentList @(
    "install",
    "--accept-license",
    "--installation-dir=D:\Docker"
    "--wsl-default-data-root=D:\Docker\wsl"
)