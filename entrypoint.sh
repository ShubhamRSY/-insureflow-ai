#!/bin/sh
set -e
PORT="${PORT:-8000}"
echo "Starting Rytera on port $PORT"
exec uvicorn insureflow.api:app --host 0.0.0.0 --port "$PORT"
