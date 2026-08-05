#!/bin/sh
set -e

# Run multiple uvicorn worker processes so one event loop is never a single
# point of failure. Pin WEB_CONCURRENCY explicitly (compose/Railway) or
# default to CPU count, capped at 4.
WEB_CONCURRENCY="${WEB_CONCURRENCY:-}"
if [ -z "$WEB_CONCURRENCY" ]; then
    NPROC="$(python3 -c 'import os; print(os.cpu_count() or 1)' 2>/dev/null || echo 1)"
    if [ "$NPROC" -gt 4 ]; then
        WEB_CONCURRENCY=4
    else
        WEB_CONCURRENCY="$NPROC"
    fi
fi

exec python3 -m uvicorn insureflow.api:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers "$WEB_CONCURRENCY"
