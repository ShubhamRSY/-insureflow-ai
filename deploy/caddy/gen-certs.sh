#!/usr/bin/env bash
# Generate local TLS certs for bank compose profile (requires mkcert).
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$DIR/certs"
if command -v mkcert >/dev/null 2>&1; then
  mkcert -cert-file "$DIR/certs/localhost.pem" -key-file "$DIR/certs/localhost-key.pem" localhost 127.0.0.1 ::1
  echo "Wrote mkcert certs to $DIR/certs"
else
  openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout "$DIR/certs/localhost-key.pem" \
    -out "$DIR/certs/localhost.pem" \
    -days 365 \
    -subj "/CN=localhost"
  echo "Wrote self-signed openssl certs to $DIR/certs (browsers will warn)"
fi
