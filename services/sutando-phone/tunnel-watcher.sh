#!/bin/bash
# tunnel-watcher.sh — self-heal the sutando phone server when the cloudflared
# quick tunnel rotates its URL.
#
# Problem: cloudflared quick tunnel gets a NEW https://*.trycloudflare.com URL
# every time the tunnel daemon restarts (crash / network blip / launchd respawn).
# sutando reads the tunnel URL ONCE at startup (TWILIO_WEBHOOK_URL). When the URL
# rotates, sutando keeps using the dead old URL → Twilio TwiML callback fails →
# caller hears "application error, goodbye".
#
# Fix: every 30s, compare the live tunnel URL (anicca_phone_url.txt, written by
# tunnel.sh) against the URL sutando is actually serving (/health webhookUrl).
# If they differ, restart sutando so it re-reads the current URL.
#
# Permanent alternative (not done): cloudflared NAMED tunnel with a fixed
# hostname (phone.aniccaai.com) — needs Cloudflare account + DNS. This watcher
# avoids that setup and self-heals the quick tunnel.
set -uo pipefail

URL_FILE="$HOME/.openclaw/state/anicca_phone_url.txt"
HEALTH="http://localhost:3100/health"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOOP_CLI="${MR_BOT_LOOP_CLI:-$ROOT/bin/lm-loop}"
SLEEP_SECONDS="${TUNNEL_WATCH_SLEEP_SECONDS:-30}"

while true; do
  sleep "$SLEEP_SECONDS"
  # current live tunnel URL (written by tunnel.sh)
  want=$(cat "$URL_FILE" 2>/dev/null | tr -d '[:space:]')
  [ -z "$want" ] && continue
  # URL sutando is actually using
  got=$(curl -s -m 5 "$HEALTH" 2>/dev/null \
        | /opt/homebrew/bin/python3 -c "import json,sys; print(json.load(sys.stdin).get('webhookUrl',''))" 2>/dev/null)
  # if sutando is up AND its URL differs from the live tunnel → restart sutando
  if [ -n "$got" ] && [ "$want" != "$got" ]; then
    echo "$(date '+%H:%M:%S') tunnel rotated: sutando=$got live=$want → restarting sutando"
    "$LOOP_CLI" restart phone-conversation
  fi
  [ "${TUNNEL_WATCH_ONCE:-0}" = "1" ] && exit 0
done
