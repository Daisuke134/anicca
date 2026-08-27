#!/bin/bash
# Start sutando phone-conversation conversation-server with env + tunnel URL.
set -uo pipefail
set -a; . "$HOME/.openclaw/.env"; set +a
# Wait for tunnel to write a URL (max 60s); fall back to NGROK_AUTHTOKEN if set.
URL_FILE="$HOME/.openclaw/state/anicca_phone_url.txt"
for i in $(seq 1 12); do
  if [ -f "$URL_FILE" ] && [ -s "$URL_FILE" ]; then
    export TWILIO_WEBHOOK_URL=$(cat "$URL_FILE")
    break
  fi
  sleep 5
done
export PHONE_PORT=3100
cd "$HOME/research/pipecat/sutando"
exec /opt/homebrew/bin/npx tsx skills/phone-conversation/scripts/conversation-server.ts
