#!/bin/bash
set -e

# Docker entrypoint script for ads-decision-platform

echo "Starting ads-decision-platform..."
echo "Python version: $(python --version)"
echo "Working directory: $(pwd)"

# Check if artifacts directory exists
if [ ! -d "/app/artifacts" ]; then
    echo "WARNING: /app/artifacts directory not found"
fi

# Optional: Wait for dependencies (database, cache, etc.)
# if [ -n "$WAIT_FOR_HOST" ]; then
#     echo "Waiting for $WAIT_FOR_HOST..."
#     timeout 60 bash -c "until nc -z $WAIT_FOR_HOST; do sleep 1; done"
# fi

# Optional: Run migrations or setup tasks
# python scripts/setup_artifacts.py

# Execute the main command
exec "$@"
