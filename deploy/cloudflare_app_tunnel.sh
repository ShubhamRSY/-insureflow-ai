#!/usr/bin/env bash
# Wire https://app.ryterainc.com → local Rytera (Cloudflare Tunnel)
# Prerequisites: cloudflared installed; domain ryterainc.com Active on Cloudflare
set -euo pipefail

ORIGIN="${ORIGIN:-http://127.0.0.1:18000}"
TUNNEL_NAME="${TUNNEL_NAME:-rytera}"
HOSTNAME="${HOSTNAME:-app.ryterainc.com}"

if ! curl -s -m 3 "$ORIGIN/health" | grep -q ok; then
  echo "ERROR: origin $ORIGIN/health not up. Start bank stack + rytera-pub first."
  exit 1
fi

echo "1) Browser will open — log into Cloudflare and authorize the cert for ryterainc.com"
cloudflared tunnel login

echo "2) Create tunnel (ok if it already exists)"
cloudflared tunnel create "$TUNNEL_NAME" 2>/dev/null || cloudflared tunnel list | grep -i "$TUNNEL_NAME" || true

echo "3) DNS route $HOSTNAME → tunnel $TUNNEL_NAME"
cloudflared tunnel route dns "$TUNNEL_NAME" "$HOSTNAME"

UUID="$(cloudflared tunnel list | awk -v n="$TUNNEL_NAME" 'tolower($0) ~ tolower(n) {print $1; exit}')"
if [[ -z "$UUID" ]]; then
  echo "Could not find tunnel UUID. Run: cloudflared tunnel list"
  exit 1
fi

CONFIG="$HOME/.cloudflared/config.yml"
cat > "$CONFIG" <<EOF
tunnel: $UUID
credentials-file: $HOME/.cloudflared/$UUID.json

ingress:
  - hostname: $HOSTNAME
    service: $ORIGIN
  - service: http_status:404
EOF

echo "Wrote $CONFIG"
echo "4) Starting tunnel — leave this running:"
echo "   https://$HOSTNAME/dashboard"
exec cloudflared tunnel run "$TUNNEL_NAME"
