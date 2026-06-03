#!/bin/bash
# Boots the x402 Hono server on :8403 ONLY. Cloudflared lives in its own plist
# (ai.anicca.x402-tunnel) so server respawns no longer rotate the public URL.
#
# Compatible with macOS /bin/bash 3.2.

set -u

ENDPOINT_DIR="/Users/anicca/anicca-oss/.worktrees/earn-x402/services/x402-endpoint"
TSX="${ENDPOINT_DIR}/node_modules/.bin/tsx"
SERVER_LOG="/tmp/anicca-x402.log"

cd "${ENDPOINT_DIR}" || exit 1

echo "[$(date -u +%FT%TZ)] run.sh boot pid=$$ (server-only)" >>"${SERVER_LOG}"

# Reap stale instances so launchd restart never collides.
pkill -f 'tsx.*server\.ts' 2>/dev/null || true
sleep 2

# launchd watches this process; exec to replace bash with the Node tsx loader.
exec "${TSX}" server.ts >>"${SERVER_LOG}" 2>&1
