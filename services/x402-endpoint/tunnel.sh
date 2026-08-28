#!/bin/bash
# Cloudflared QUICK tunnel for the x402 endpoint. Decoupled from the server plist
# so a server restart (e.g. picking up new code) does NOT rotate the public URL.
#
# Persists the live URL to ~/.openclaw/state/anicca_x402_url.txt; consumers
# (agentic-market.json bumper cron, tweets, monitor) read from there.
#
# Compatible with macOS /bin/bash 3.2.

set -u

TUNNEL_LOG="/tmp/anicca-x402-cloudflared.log"
URL_FILE="${HOME}/.openclaw/state/anicca_x402_url.txt"

mkdir -p "${HOME}/.openclaw/state"

# Reset the tunnel log on every boot so the URL harvester sees ONLY this run's URL.
: >"${TUNNEL_LOG}"

# Wait for the local server to bind :8403 before starting the tunnel — otherwise
# cloudflared will issue a URL that 502s for the first ~15s.
echo "[$(date -u +%FT%TZ)] tunnel.sh waiting for :8403" >>"${TUNNEL_LOG}"
i=0
while [ $i -lt 120 ]; do
  if /usr/bin/curl -sf http://localhost:8403/health >/dev/null 2>&1; then
    break
  fi
  sleep 2
  i=$((i + 1))
done
echo "[$(date -u +%FT%TZ)] :8403 healthy, launching cloudflared" >>"${TUNNEL_LOG}"

# Harvest URL in background.
(
  k=0
  while [ $k -lt 30 ]; do
    URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "${TUNNEL_LOG}" | head -n 1)
    if [ -n "${URL}" ]; then
      # Atomic write to canonical state (consumer cron, listing-bumper).
      tmp="${URL_FILE}.tmp.$$"
      printf '%s\n' "${URL}" >"${tmp}" && mv "${tmp}" "${URL_FILE}"
      echo "[$(date -u +%FT%TZ)] tunnel live: ${URL}" >>"${TUNNEL_LOG}"
      break
    fi
    sleep 2
    k=$((k + 1))
  done
) &

# Exec so launchd can supervise cloudflared directly. KeepAlive=true will
# respawn the wrapper (which respawns cloudflared) on any non-zero exit.
exec /opt/homebrew/bin/cloudflared tunnel --no-autoupdate --url http://localhost:8403 >>"${TUNNEL_LOG}" 2>&1
