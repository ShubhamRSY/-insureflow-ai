#!/usr/bin/env bash
# Persistently expose local Rytera bank stack via ngrok (survives terminal close).
# Usage: ./deploy/public_tunnel.sh
# Branded (paid ngrok / custom DNS): NGROK_DOMAIN=app.rytera.ai ./deploy/public_tunnel.sh

set -euo pipefail
TARGET="${TUNNEL_TARGET:-https://localhost:8443}"
DOMAIN="${NGROK_DOMAIN:-}"
LOG="${NGROK_LOG:-/tmp/ngrok-rytera.log}"
PIDFILE="${NGROK_PIDFILE:-/tmp/ngrok-rytera.pid}"
NGROK_BIN="$(command -v ngrok || true)"

if [[ -z "$NGROK_BIN" ]]; then
  echo "ERROR: ngrok not found. Install: brew install ngrok/ngrok/ngrok"
  exit 1
fi

if ! curl -sk -m 3 "$TARGET/health" >/dev/null 2>&1; then
  echo "ERROR: $TARGET/health not reachable. Start the bank stack first."
  exit 1
fi

# Stop previous tunnel
if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  kill "$(cat "$PIDFILE")" 2>/dev/null || true
  sleep 1
fi
pkill -f "$NGROK_BIN http" 2>/dev/null || true
sleep 1

ARGS=(http "$TARGET" --log=stdout --log-format=logfmt)
if [[ -n "$DOMAIN" ]]; then
  ARGS+=(--url="https://$DOMAIN")
  echo "Starting branded tunnel: https://$DOMAIN"
else
  echo "Starting free ngrok tunnel (URL changes each restart)…"
fi

nohup "$NGROK_BIN" "${ARGS[@]}" >"$LOG" 2>&1 </dev/null &
echo $! >"$PIDFILE"
disown $! 2>/dev/null || true
sleep 5

if ! kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "Tunnel failed to stay up. Log:"
  tail -40 "$LOG"
  exit 1
fi

URL="$(curl -s http://127.0.0.1:4040/api/tunnels | python3 -c "import sys,json; t=json.load(sys.stdin).get('tunnels') or []; print(t[0]['public_url'] if t else '')")"
if [[ -z "$URL" ]]; then
  echo "Tunnel API empty. Log:"
  tail -40 "$LOG"
  exit 1
fi

echo ""
echo "Rytera is ONLINE (pid $(cat "$PIDFILE"))"
echo "  Dashboard: $URL/dashboard"
echo "  Health:    $URL/health"
echo "  Stop:      kill \$(cat $PIDFILE)"
echo ""
echo "Keep this Mac awake; free URLs change if you restart the tunnel."
