#!/bin/sh
# T-105 demo replay on a temp copy (D-069). Usage: run-demo.sh <new empty folder>
# Needs LLM_BASE_URL / LLM_MODEL from the shell (Groq host, qwen/qwen3.8-27b) so saved-reply keys match.
set -e
T=${1:?give a new empty folder}; HERE=$(cd "$(dirname "$0")" && pwd); W=$(cd "$HERE/../../.." && pwd)
mkdir -p "$T/inbox" "$T/cache" "$T/pngs"
for n in $(seq 127 153); do cp -R "$W/simulation/inbox/SUB-$n" "$T/inbox/"; done
cp -R "$HERE/saved-replies/extractions" "$T/cache/"
cp "$HERE"/*.py "$T/"
export LLM_CACHE_DIR="$T/cache" LLM_PACE_SECONDS=0
cd "$T"
"$W/.venv/bin/python" drive.py "$T"         # saved replies only; live calls are blocked
rm -rf "$T/box"
"$W/.venv/bin/python" shotflow.py "$T"      # replays the demo steps, pages in $T/shots/
"$W/.venv/bin/python" snap.py "$T/pngs" "$T/shots" 2>/dev/null || echo "PNGs skipped (playwright not in .venv); open the pages in $T/shots in a browser"
echo "Pages: $T/shots  PNGs: $T/pngs"
