#!/bin/sh
# Docker entrypoint script that reads API_PORT from environment
# Uses exec to ensure proper signal handling

set -e

# Get port from environment variable, default to 8100
PORT="${API_PORT:-8100}"

# Execute uvicorn with the configured port
exec python -m uvicorn recipe_ingest.api.app:create_app \
    --factory \
    --host 0.0.0.0 \
    --port "$PORT"

