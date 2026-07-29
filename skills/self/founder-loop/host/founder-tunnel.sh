#!/usr/bin/env bash
# founder-tunnel.sh — KeepAlive launchd: a cloudflared quick tunnel for the FOUNDER seller (:8410), persisting the
# live public URL to the founder's OWN state file (NOT the shared $HOME/.local/state/life-manager one) so the loop + the listing read it.
set -u
PORT=8410
URL_FILE="$HOME/.anicca-founder/state/seller-url.txt"
TLOG="/tmp/founder-x402-tunnel.log"
mkdir -p "$(dirname "$URL_FILE")"
# wait for the founder seller to be healthy on :8410 before tunnelling
for i in $(seq 1 60); do curl -sf --max-time 3 "http://localhost:$PORT/" >/dev/null 2>&1 && break; sleep 2; done
: > "$TLOG"
/opt/homebrew/bin/cloudflared tunnel --url "http://localhost:$PORT" >>"$TLOG" 2>&1 &
CF=$!
# extract + atomically persist the live trycloudflare URL to the founder state file
for i in $(seq 1 30); do
  URL="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$TLOG" | head -1)"
  if [ -n "$URL" ]; then tmp="$URL_FILE.tmp.$$"; printf '%s\n' "$URL" > "$tmp" && mv "$tmp" "$URL_FILE"; break; fi
  sleep 1
done
wait "$CF"   # if cloudflared exits, this script exits → launchd KeepAlive respawns it (and re-persists a fresh URL)
