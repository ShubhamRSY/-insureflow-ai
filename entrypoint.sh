#!/bin/sh
set -e
PORT="${PORT:-8000}"
echo "=== RYTERA ENTRYPOINT: starting on port $PORT ==="
exec python3 -m uvicorn insureflow.api:app --host 0.0.0.0 --port "$PORT"
