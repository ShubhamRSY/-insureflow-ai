#!/bin/sh
set -e
exec python3 -m uvicorn insureflow.api:app --host 0.0.0.0 --port "${PORT:-8000}"
