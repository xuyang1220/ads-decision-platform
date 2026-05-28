# Multi-stage Dockerfile for ads-decision-platform serving API
FROM python:3.10-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create app user for security
RUN groupadd -r appuser && useradd -r -m -g appuser appuser

WORKDIR /app

# ============================================================
# Stage: builder - install dependencies
# ============================================================
FROM base as builder

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install Python dependencies
RUN pip install --user --no-warn-script-location -e .

# ============================================================
# Stage: runtime - minimal production image
# ============================================================
FROM base as runtime

# Copy Python packages from builder into appuser's home
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY src/ ./src/
COPY artifacts/ ./artifacts/

# Make sure scripts are in PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Change ownership to appuser
RUN chown -R appuser:appuser /app /home/appuser/.local

# Switch to non-root user
USER appuser

# Expose port for FastAPI
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the FastAPI application with uvicorn
CMD ["uvicorn", "ads_platform.serving.api:app", "--host", "0.0.0.0", "--port", "8000"]
