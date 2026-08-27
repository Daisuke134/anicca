#!/bin/bash
# cloudflared tunnel for sutando phone-conversation (port 3100).
# Persists URL to anicca_phone_url.txt for lateness_check + readers.
set -euo pipefail
PORT=3100
URL_FILE="$HOME/.openclaw/state/anicca_phone_url.txt"
mkdir -p "$(dirname "$URL_FILE")"
# Wait for sutando to bind :3100
for i in $(seq 1 24); do
  lsof -nP -iTCP:$PORT -sTCP:LISTEN -t >/dev/null 2>&1 && break
  sleep 5
done
exec /opt/homebrew/bin/cloudflared tunnel --no-autoupdate --url "http://localhost:$PORT" 2>&1 \
  | awk -v urlfile="$URL_FILE" '
      /https:\/\/[a-z0-9-]+\.trycloudflare\.com/ {
        match($0, /https:\/\/[a-z0-9-]+\.trycloudflare\.com/)
        url = substr($0, RSTART, RLENGTH)
        if (url != last) { print url > urlfile; close(urlfile); last = url }
      }
      { print }'
