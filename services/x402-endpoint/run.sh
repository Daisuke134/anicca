#!/bin/bash
# Boots the x402 endpoint + Cloudflare quick tunnel.
# Intended to be invoked by launchd (~/Library/LaunchAgents/ai.anicca.x402-endpoint.plist).
#
# Side effects:
#   - Listens on :8403 (Hono via tsx)
#   - Starts cloudflared tunnel; writes the live https URL to
#     ~/.openclaw/state/anicca_x402_url.txt so consumers (cron, listings) pick
#     it up on every fire (mirrors the pipecat-phone pattern).
#   - Combined logs at /tmp/anicca-x402.log + /tmp/anicca-x402-cloudflared.log
#
# Compatible with macOS /bin/bash 3.2 (no `wait -n`).

set -u

ENDPOINT_DIR="/Users/anicca/anicca-oss/.worktrees/earn-x402/services/x402-endpoint"
TSX="${ENDPOINT_DIR}/node_modules/.bin/tsx"
SERVER_LOG="/tmp/anicca-x402.log"
TUNNEL_LOG="/tmp/anicca-x402-cloudflared.log"
URL_FILE="${HOME}/.openclaw/state/anicca_x402_url.txt"

mkdir -p "${HOME}/.openclaw/state"

cd "${ENDPOINT_DIR}" || exit 1

echo "[$(date -u +%FT%TZ)] run.sh boot pid=$$" >>"${SERVER_LOG}"

# Reap any stale instances so launchd restart never collides.
pkill -f 'tsx.*server\.ts' 2>/dev/null || true
pkill -f 'cloudflared.*localhost:8403' 2>/dev/null || true
sleep 2

# Start Hono server.
"${TSX}" server.ts >>"${SERVER_LOG}" 2>&1 &
SERVER_PID=$!
echo "[$(date -u +%FT%TZ)] tsx server.ts pid=${SERVER_PID}" >>"${SERVER_LOG}"

# Wait for the port to be live (max 90s — tsx cold start under launchd takes
# ~25-30s on first boot; subsequent restarts are faster but we keep headroom).
BOUND=0
i=0
while [ $i -lt 90 ]; do
  if curl -sf http://localhost:8403/health >/dev/null 2>&1; then
    BOUND=1
    break
  fi
  sleep 1
  i=$((i + 1))
done

if [ $BOUND -ne 1 ]; then
  echo "[$(date -u +%FT%TZ)] FATAL: server failed to bind :8403 after 90s" >>"${SERVER_LOG}"
  kill -9 "${SERVER_PID}" 2>/dev/null || true
  exit 1
fi

echo "[$(date -u +%FT%TZ)] :8403 healthy, launching cloudflared" >>"${SERVER_LOG}"

# Start cloudflared quick tunnel.
: >"${TUNNEL_LOG}"
cloudflared tunnel --no-autoupdate --url http://localhost:8403 >>"${TUNNEL_LOG}" 2>&1 &
TUNNEL_PID=$!
echo "[$(date -u +%FT%TZ)] cloudflared pid=${TUNNEL_PID}" >>"${SERVER_LOG}"

# Harvest the trycloudflare URL (max ~60s) and persist it.
(
  k=0
  while [ $k -lt 30 ]; do
    URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "${TUNNEL_LOG}" | head -n 1)
    if [ -n "${URL}" ]; then
      printf '%s\n' "${URL}" >"${URL_FILE}"
      echo "[$(date -u +%FT%TZ)] tunnel live: ${URL}" >>"${SERVER_LOG}"
      break
    fi
    sleep 2
    k=$((k + 1))
  done
) &

# Monitor both children; if either dies, tear down and let launchd respawn.
while kill -0 "${SERVER_PID}" 2>/dev/null && kill -0 "${TUNNEL_PID}" 2>/dev/null; do
  sleep 5
done

echo "[$(date -u +%FT%TZ)] child died — tearing down (server_alive=$(kill -0 ${SERVER_PID} 2>/dev/null && echo yes || echo no) tunnel_alive=$(kill -0 ${TUNNEL_PID} 2>/dev/null && echo yes || echo no))" >>"${SERVER_LOG}"

kill -9 "${SERVER_PID}" "${TUNNEL_PID}" 2>/dev/null || true
exit 1
