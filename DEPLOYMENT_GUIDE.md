# Local Deployment Guide - From Scratch

Complete step-by-step instructions to deploy the ads-decision-platform API locally with no dependencies installed.

## Prerequisites

You need to install:
- **Docker** (20.10+) and **Docker Compose** (2.0+)
- **Git** (to clone the repo if needed)

That's it! Everything else runs inside containers.

---

## Option 1: Docker Deployment (Recommended - Zero Local Setup)

### Step 1: Install Docker

#### macOS
```bash
# Download and install Docker Desktop from:
# https://www.docker.com/products/docker-desktop

# Or via Homebrew:
brew install --cask docker

# Start Docker Desktop, then verify:
docker --version
docker-compose --version
```

#### Linux (Ubuntu/Debian)
```bash
# Install Docker
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin

# Add your user to docker group (logout/login required)
sudo usermod -aG docker $USER

# Verify
docker --version
docker compose version
```

#### Windows
```bash
# Download and install Docker Desktop from:
# https://www.docker.com/products/docker-desktop

# Verify in PowerShell or WSL2:
docker --version
docker-compose --version
```

### Step 2: Clone and Navigate to Repository

```bash
git clone <repository-url>
cd ads-decision-platform
```

### Step 3: Build and Start the Service

```bash
# Quick start - build and run
docker-compose up --build

# OR run in detached mode (background)
docker-compose up -d --build

# OR use the Makefile shorthand
make up-build
```

**What happens:**
- Docker builds a Python 3.10 image with all dependencies
- Installs `pydantic`, `fastapi`, `uvicorn`, `torch`
- Copies your source code and artifacts into the container
- Starts the FastAPI server on port 8000

**Expected output:**
```
[+] Building 45.2s (15/15) FINISHED
[+] Running 1/1
 ✔ Container ads-decision-api  Started
```

### Step 4: Verify Service is Running

```bash
# Check container status
docker ps

# Check health endpoint
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# Or use the Makefile
make health

# View logs
docker-compose logs -f ads-api
# OR
make logs
```

### Step 5: Test the Decision API

```bash
# Simple test request
curl -X POST http://localhost:8000/decide \
  -H "Content-Type: application/json" \
  -d '{
    "request": {
      "request_id": "test_001",
      "timestamp_ms": 1609459200000,
      "device_type": "mobile",
      "country": "US",
      "placement": "feed",
      "app_or_site": "app_123"
    },
    "candidates": [
      {
        "ad_id": "ad_1",
        "campaign_id": "cmp_demo",
        "adgroup_id": "ag_1",
        "base_bid": 1.5,
        "features": {
          "I1": "5",
          "I2": "10",
          "I3": "15",
          "I4": "20",
          "I5": "25",
          "I6": "30",
          "I7": "35",
          "I8": "40",
          "I9": "45",
          "I10": "50",
          "I11": "55",
          "I12": "60",
          "I13": "65",
          "C1": "abc",
          "C2": "def",
          "C3": "ghi",
          "C4": "jkl",
          "C5": "mno",
          "C6": "pqr",
          "C7": "stu",
          "C8": "vwx",
          "C9": "yza",
          "C10": "bcd",
          "C11": "efg",
          "C12": "hij",
          "C13": "klm",
          "C14": "nop",
          "C15": "qrs",
          "C16": "tuv",
          "C17": "wxy",
          "C18": "zab",
          "C19": "cde",
          "C20": "fgh",
          "C21": "ijk",
          "C22": "lmn",
          "C23": "opq",
          "C24": "rst",
          "C25": "uvw",
          "C26": "xyz"
        }
      },
      {
        "ad_id": "ad_2",
        "campaign_id": "cmp_demo",
        "adgroup_id": "ag_2",
        "base_bid": 1.2,
        "features": {
          "I1": "3",
          "I2": "8",
          "I3": "12",
          "I4": "18",
          "I5": "22",
          "I6": "28",
          "I7": "32",
          "I8": "38",
          "I9": "42",
          "I10": "48",
          "I11": "52",
          "I12": "58",
          "I13": "62",
          "C1": "aaa",
          "C2": "bbb",
          "C3": "ccc",
          "C4": "ddd",
          "C5": "eee",
          "C6": "fff",
          "C7": "ggg",
          "C8": "hhh",
          "C9": "iii",
          "C10": "jjj",
          "C11": "kkk",
          "C12": "lll",
          "C13": "mmm",
          "C14": "nnn",
          "C15": "ooo",
          "C16": "ppp",
          "C17": "qqq",
          "C18": "rrr",
          "C19": "sss",
          "C20": "ttt",
          "C21": "uuu",
          "C22": "vvv",
          "C23": "www",
          "C24": "xxx",
          "C25": "yyy",
          "C26": "zzz"
        }
      }
    ]
  }'
```

### Step 6: Management Commands

```bash
# Stop the service
docker-compose down
# OR
make down

# View logs (last 100 lines)
docker-compose logs --tail=100 ads-api

# Open shell inside running container
docker exec -it ads-decision-api bash
# OR
make shell

# Restart after changes
docker-compose restart
# OR
make restart

# Complete cleanup (remove containers, images, volumes)
docker-compose down -v --rmi all
# OR
make clean
```

### Step 7: Updating Models (Without Rebuilding)

The artifacts directory is mounted as a volume, so you can update models without rebuilding:

```bash
# Update a model artifact
cp new_model.pt artifacts/criteo_bundle/deepfm_criteo.pt

# Restart the service
docker-compose restart

# The new model is loaded automatically
```

### Step 8: Test the Decision API

Consider periodically run scripts/DockerClean.ps1 to free disk spaces for Docker in WSL. See the script for details.

---

## Option 2: Local Python Environment (For Development)

If you want to run without Docker for development:

### Step 1: Install Python 3.10+

#### macOS
```bash
brew install python@3.10
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install -y python3.10 python3.10-venv python3-pip
```

#### Windows
Download Python 3.10+ from https://www.python.org/downloads/

### Step 2: Set Up Virtual Environment

```bash
cd ads-decision-platform

# Create virtual environment
python3.10 -m venv .venv

# Activate it
# On Linux/macOS:
source .venv/bin/activate

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1

# On Windows (CMD):
.venv\Scripts\activate.bat
```

### Step 3: Install Dependencies

```bash
# Install the package in editable mode with dev dependencies
pip install -e .[dev]

# This installs:
# - pydantic>=2.6,<3
# - fastapi>=0.110,<1
# - uvicorn>=0.29,<1
# - torch>=2.2,<3
# - pytest>=8.0,<9 (dev)
```

### Step 4: Run the Server

```bash
# Start the FastAPI server
uvicorn ads_platform.serving.api:app --host 0.0.0.0 --port 8000 --reload

# The --reload flag enables auto-reload on code changes (development only)
```

### Step 5: Test Endpoints

```bash
# In another terminal (same venv activated):
curl http://localhost:8000/health

# Run the test suite
pytest -v

# Run specific test
pytest tests/unit/test_api.py -v
```

### Step 6: Stop the Server

Press `Ctrl+C` in the terminal running uvicorn.

---

## Option 3: Production Deployment with Gunicorn (Multi-worker)

For production with multiple workers:

### Using Docker

Edit `Dockerfile` CMD or override in `docker-compose.yml`:

```yaml
services:
  ads-api:
    command: >
      uvicorn ads_platform.serving.api:app
      --host 0.0.0.0
      --port 8000
      --workers 4
```

Or use `Dockerfile.production` with Gunicorn:

```bash
docker build -f Dockerfile.production -t ads-decision-api:prod .
docker run -d -p 8000:8000 ads-decision-api:prod
```

### Using Local Python

```bash
# Install gunicorn
pip install gunicorn

# Run with uvicorn workers
gunicorn ads_platform.serving.api:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
```

---

## Verifying Your Deployment

### 1. Health Check
```bash
curl http://localhost:8000/health
# Should return: {"status":"ok"}
```

### 2. Info Endpoint (if using updated api.py)
```bash
curl http://localhost:8000/info
# Returns model versions and configuration
```

### 3. Decision Endpoint
```bash
curl -X POST http://localhost:8000/decide \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/sample_auction.json
```

### 4. Check Logs
```bash
# Docker
docker-compose logs --tail=50 ads-api

# Local
# Logs appear in the terminal where uvicorn is running
```

---

## Troubleshooting

### Port 8000 Already in Use
```bash
# Find what's using the port
# Linux/macOS:
lsof -i :8000

# Windows:
netstat -ano | findstr :8000

# Kill the process or use a different port
docker-compose down
# Edit docker-compose.yml to use different port (e.g., "8001:8000")
docker-compose up -d
```

### Docker Build Fails
```bash
# Clear Docker cache
docker builder prune -a

# Rebuild from scratch
docker-compose build --no-cache
```

### Artifacts Not Found
```bash
# Verify artifacts exist
ls -la artifacts/criteo_bundle/
ls -la artifacts/demo_bundle/

# If missing, you may need to train models:
python scripts/train_criteo_deepfm.py \
  --train-path data/criteo/train.txt \
  --output-dir artifacts/criteo_bundle \
  --max-rows 1000000

# Or use the demo bundle (smaller, for testing)
```

### Container Crashes / OOM
```bash
# Check container resources
docker stats ads-decision-api

# Increase memory in docker-compose.yml:
deploy:
  resources:
    limits:
      memory: 8G  # Increase from 4G
```

### Python Import Errors (Local)
```bash
# Ensure PYTHONPATH is set
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Or reinstall in editable mode
pip install -e .
```

---

## Next Steps

1. **Train on Real Data**: Follow `scripts/train_criteo_deepfm.py` to train your CTR model
2. **Fit Landscape Models**: Use `scripts/fit_landscape.py` with your historical auction logs
3. **Run Replays**: Test your system with `scripts/run_budget_replay.py`
4. **Add Monitoring**: Uncomment Prometheus/Grafana in `docker-compose.yml`
5. **Deploy to Cloud**: See `DOCKER_DEPLOYMENT.md` for AWS, GCP, K8s instructions

---

## Quick Reference

### Docker Commands
```bash
make build      # Build image
make up         # Start detached
make up-build   # Build + start
make down       # Stop
make logs       # Follow logs
make shell      # Open shell
make health     # Check health
make clean      # Remove everything
```

### Endpoints
- `GET  /health` - Health check
- `GET  /info` - Model info (if implemented)
- `POST /decide` - Main decision endpoint
- `GET  /docs` - Interactive API documentation (Swagger UI)
- `GET  /redoc` - Alternative API documentation

### File Structure
```
ads-decision-platform/
├── src/ads_platform/          # Source code
│   ├── serving/api.py         # FastAPI app
│   ├── decisioning/engine.py  # Decision engine
│   ├── ctr/                   # CTR models
│   ├── landscape/             # Bid landscapes
│   └── pacing/                # Budget pacing
├── artifacts/                 # Trained models
│   ├── criteo_bundle/         # Production CTR model
│   ├── demo_bundle/           # Demo CTR model
│   └── fitted_landscape_oracle.json
├── configs/                   # YAML configs
├── scripts/                   # Training/replay scripts
├── tests/                     # Test suite
├── Dockerfile                 # Development Docker image
├── Dockerfile.production      # Production Docker image
├── docker-compose.yml         # Compose configuration
└── Makefile                   # Convenience commands
```

---

## Support

For issues or questions:
1. Check existing logs: `docker-compose logs ads-api`
2. Verify artifacts are present: `ls -la artifacts/`
3. Run tests: `docker-compose run --rm ads-api pytest -v`
4. Consult `DOCKER_DEPLOYMENT.md` for advanced configuration
