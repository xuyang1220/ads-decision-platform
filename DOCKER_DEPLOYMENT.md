# Docker Deployment Guide

This guide explains how to deploy the ads-decision-platform serving API using Docker and Docker Compose.

## Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- At least 4GB RAM available for the container
- Built artifacts in `artifacts/` directory (or use the demo_bundle)

## Quick Start

### 1. Build and run with Docker Compose

```bash
# Build and start the service
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

The API will be available at `http://localhost:8000`

### 2. Test the endpoints

```bash
# Health check
curl http://localhost:8000/health

# Decision endpoint (example)
curl -X POST http://localhost:8000/decide \
  -H "Content-Type: application/json" \
  -d '{
    "auction_id": "test_001",
    "timestamp_ms": 1609459200000,
    "candidates": [
      {
        "candidate_id": "ad_1",
        "entity_id": "cmp_demo",
        "bid_price": 1.5,
        "features": {"f1": 1.0, "f2": 0.5}
      }
    ],
    "context": {},
    "num_slots": 4
  }'
```

### 3. View logs

```bash
# Follow logs
docker-compose logs -f ads-api

# View last 100 lines
docker-compose logs --tail=100 ads-api
```

### 4. Stop the service

```bash
# Stop containers
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

## Build with Docker only (no Compose)

```bash
# Build the image
docker build -t ads-decision-api:latest .

# Run the container
docker run -d \
  --name ads-api \
  -p 8000:8000 \
  -v $(pwd)/artifacts:/app/artifacts:ro \
  ads-decision-api:latest

# Check logs
docker logs -f ads-api

# Stop and remove
docker stop ads-api && docker rm ads-api
```

## Configuration

### Environment Variables

You can configure the service using environment variables in `docker-compose.yml`:

- `LOG_LEVEL`: Set logging level (debug, info, warning, error)
- `PYTHONPATH`: Python module search path (default: `/app/src`)
- `CTR_BUNDLE_PATH`: Path to CTR model bundle (optional)
- `LANDSCAPE_PATH`: Path to landscape model (optional)

### Volume Mounts

The compose file mounts `./artifacts` as read-only so you can:

1. Update models without rebuilding the image
2. Use different artifacts for different deployments

### Resource Limits

Adjust CPU/memory limits in `docker-compose.yml` under `deploy.resources`:

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 4G
    reservations:
      cpus: '0.5'
      memory: 1G
```

## Production Deployment

### Multi-worker setup

For production, run multiple uvicorn workers:

```dockerfile
# Modify CMD in Dockerfile:
CMD ["uvicorn", "ads_platform.serving.api:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4"]
```

Or set via environment variable and custom entrypoint script.

### Load Balancer

Put multiple containers behind nginx or cloud load balancer:

```yaml
# docker-compose.yml
services:
  ads-api:
    # ... existing config
    deploy:
      replicas: 3
```

### Use Production ASGI Server

For high traffic, consider using gunicorn with uvicorn workers:

```bash
pip install gunicorn
gunicorn ads_platform.serving.api:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Monitoring

Uncomment the Prometheus and Grafana services in `docker-compose.yml` to enable monitoring.

You'll need to:
1. Instrument the FastAPI app with prometheus-fastapi-instrumentator
2. Create `monitoring/prometheus.yml` config
3. Set up Grafana dashboards

## Cloud Deployment

### AWS ECS/Fargate

```bash
# Tag and push to ECR
docker tag ads-decision-api:latest <account>.dkr.ecr.<region>.amazonaws.com/ads-decision-api:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/ads-decision-api:latest

# Create ECS task definition and service
# Use artifacts from S3 or EFS volume
```

### Google Cloud Run

```bash
# Build and push to GCR
docker tag ads-decision-api:latest gcr.io/<project>/ads-decision-api:latest
docker push gcr.io/<project>/ads-decision-api:latest

# Deploy
gcloud run deploy ads-decision-api \
  --image gcr.io/<project>/ads-decision-api:latest \
  --platform managed \
  --region us-central1 \
  --memory 4Gi \
  --cpu 2
```

### Kubernetes

Create deployment and service manifests:

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ads-decision-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ads-api
  template:
    metadata:
      labels:
        app: ads-api
    spec:
      containers:
      - name: api
        image: ads-decision-api:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        volumeMounts:
        - name: artifacts
          mountPath: /app/artifacts
          readOnly: true
      volumes:
      - name: artifacts
        persistentVolumeClaim:
          claimName: ads-artifacts-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: ads-decision-api
spec:
  type: LoadBalancer
  selector:
    app: ads-api
  ports:
  - port: 80
    targetPort: 8000
```

## Troubleshooting

### Container won't start

Check logs:
```bash
docker-compose logs ads-api
```

Common issues:
- Missing artifacts directory
- Port 8000 already in use
- Insufficient memory

### Health check failing

Test manually inside container:
```bash
docker exec -it ads-decision-api bash
curl http://localhost:8000/health
```

### Model loading errors

Ensure artifacts are properly mounted:
```bash
docker exec -it ads-decision-api ls -la /app/artifacts
```

## Security Notes

- The Dockerfile runs as non-root user `appuser`
- Artifacts are mounted read-only
- No sensitive credentials in image (use secrets management)
- Keep base images updated: `docker-compose pull && docker-compose up --build`
