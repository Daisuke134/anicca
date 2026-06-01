#!/bin/bash
# Idempotent: make sure the imokenet realtime bridge is up and reachable.
# Prints the current public URL on success. Kicks the launchd service if down.
set -uo pipefail

URL_FILE="$HOME/.openclaw/workspace/imokenet/state/public_url.txt"
FUNNEL_URL="https://aniccanomac-mini-1.tail7a0ba4.ts.net"   # stable Tailscale Funnel
LABEL="ai.openclaw.imokenet"
UID_NUM="$(id -u)"

healthy() { curl -s --max-time 10 "$1/healthz" 2>/dev/null | grep -q '"ok":true'; }

check() {
  # Prefer the stable Funnel URL once its public DNS/cert is live; else the
  # ephemeral quick-tunnel URL written by run-bridge.sh.
  if healthy "$FUNNEL_URL"; then echo "$FUNNEL_URL" > "$URL_FILE"; echo "$FUNNEL_URL"; return 0; fi
  local url; url="$(cat "$URL_FILE" 2>/dev/null)"
  [ -z "$url" ] && return 1
  [ "$url" = "$FUNNEL_URL" ] && return 1   # funnel was stale, don't loop on it
  healthy "$url" || return 1
  echo "$url"; return 0
}

if URL="$(check)"; then
  echo "[ensure-bridge] healthy: $URL"; exit 0
fi

echo "[ensure-bridge] bridge down -> (re)bootstrapping launchd $LABEL"
launchctl kickstart -k "gui/$UID_NUM/$LABEL" 2>/dev/null \
  || launchctl bootstrap "gui/$UID_NUM" "$HOME/Library/LaunchAgents/$LABEL.plist" 2>/dev/null

for i in $(seq 1 30); do
  sleep 1
  if URL="$(check)"; then echo "[ensure-bridge] recovered: $URL"; exit 0; fi
done

echo "[ensure-bridge] FAILED to bring bridge up"; exit 1
