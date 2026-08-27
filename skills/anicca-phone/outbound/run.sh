#!/bin/bash
# run.sh — Pipecat phone stack supervisor (cloudflared + uvicorn server.py).
#
# Boots a cloudflared quick tunnel, captures the public URL, then exec's the
# Pipecat outbound server with that URL wired in as LOCAL_SERVER_URL. Designed
# to be launched by launchd (KeepAlive=true, RunAtLoad=true) so the whole
# stack survives reboots and self-heals on crash.
#
# Side effects:
#   - cloudflared log         → /tmp/anicca-pipecat-cloudflared.log
#   - tunnel URL persisted to → ~/.openclaw/state/anicca_phone_url.txt
#     (lateness_check.py reads this to know where /dialout lives)
#
# Secrets come from ~/.openclaw/.env (gitignored). No secrets in this file.

set -euo pipefail

REPO_DIR="${HOME}/.openclaw/skills/anicca-phone/outbound"
STATE_DIR="$HOME/.openclaw/state"
STATE_FILE="$STATE_DIR/anicca_phone_url.txt"
CF_LOG="/tmp/anicca-pipecat-cloudflared.log"
PORT="${PORT:-7860}"

mkdir -p "$STATE_DIR"

# Load owner env (TWILIO_*, GEMINI_API_KEY, etc.) — never commit these.
set -a
# shellcheck source=/dev/null
source "$HOME/.openclaw/.env"
set +a

# Reap any previously-orphaned tunnel pointing at our port (e.g. from a
# previous run that died ungracefully). launchd's KeepAlive doesn't clean up
# children we backgrounded ourselves.
pkill -f "cloudflared tunnel --url http://localhost:$PORT" 2>/dev/null || true

# Also reap any orphan process holding the port (e.g. an earlier hand-started
# `python server.py` from local dev). Without this the new uvicorn would hit
# "address already in use" and launchd would crash-loop on KeepAlive.
ORPHAN_PIDS=$(lsof -ti tcp:"$PORT" 2>/dev/null || true)
if [ -n "$ORPHAN_PIDS" ]; then
  echo "[run.sh] killing orphan(s) on port $PORT: $ORPHAN_PIDS" >&2
  kill -9 $ORPHAN_PIDS 2>/dev/null || true
fi
sleep 1

# Boot the tunnel and capture its public URL by tailing its log. We use the
# free quick-tunnel here (trycloudflare.com); upgrading to a named tunnel
# (固定 hostname) is a follow-up — the consumers all read STATE_FILE so the
# URL being dynamic is fine as long as the file is current.
nohup /opt/homebrew/bin/cloudflared tunnel --url "http://localhost:$PORT" \
  > "$CF_LOG" 2>&1 &
CF_PID=$!
echo "[run.sh] cloudflared pid=$CF_PID"

# Wait up to 30s for cloudflared to print the URL.
# CRITICAL: cloudflared logs its OWN management API endpoint as
# 'https://api.trycloudflare.com' BEFORE the tunnel is up. If the regex
# matches that, Twilio's webhook breaks and the operator hears Twilio's
# default TTS instead of Gemini Live Charon (the "shitty AI voice"
# failure, observed 2026-06-01 ~09:45 JST). Excluding 'api.' + requiring
# at least one internal hyphen matches only the real "random-word-word"
# subdomain format.
TUNNEL_URL=""
for _ in $(seq 1 30); do
  TUNNEL_URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$CF_LOG" \
                | grep -v 'https://api\.trycloudflare\.com' \
                | grep -E 'https://[a-z0-9]+-[a-z0-9-]+\.trycloudflare\.com' \
                | head -n 1 || true)
  if [ -n "$TUNNEL_URL" ]; then break; fi
  sleep 1
done

# Sanity smoke test the URL actually routes to the local server before
# handing it off to Pipecat / Twilio. A tunnel that's "up" per cloudflared
# but not yet fully routed yields 502 or hangs — better to crash here so
# launchd retries than to ship a broken URL to Twilio.
if [ -n "$TUNNEL_URL" ]; then
  for _ in $(seq 1 10); do
    if curl -sf --max-time 5 "$TUNNEL_URL" > /dev/null 2>&1 \
       || curl -sf --max-time 5 -o /dev/null -X POST "$TUNNEL_URL/dialout" \
            -H 'Content-Type: application/json' -d '{}'; then
      break
    fi
    sleep 2
  done
fi

if [ -z "$TUNNEL_URL" ]; then
  echo "[run.sh] cloudflared did not produce a URL within 30s — aborting" >&2
  kill "$CF_PID" 2>/dev/null || true
  exit 1
fi

echo "$TUNNEL_URL" > "$STATE_FILE"
echo "[run.sh] tunnel URL=$TUNNEL_URL  (persisted to $STATE_FILE)"

# Trap signals so launchd's stop/relaunch tears the tunnel down too.
trap 'kill "$CF_PID" 2>/dev/null || true' EXIT INT TERM

cd "$REPO_DIR"
# shellcheck source=/dev/null
source venv/bin/activate

# Exec uvicorn-style server (server.py runs uvicorn internally) so launchd
# tracks Python as the foreground process.
exec env \
  PORT="$PORT" \
  ENV=local \
  LOCAL_SERVER_URL="$TUNNEL_URL" \
  ANICCA_PHONE_DIALOUT_URL="$TUNNEL_URL" \
  python server.py
