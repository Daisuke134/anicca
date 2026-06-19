#!/usr/bin/env bash
# anicca-daemon.sh — the supervised, self-updating entrypoint for a living Anicca.
#
# Run under a KeepAlive supervisor (macOS launchd, Linux systemd, or Docker `restart: always`). The
# supervisor restarts this script whenever it exits, so Anicca stands on its own — no human runs it
# by hand. On every (re)start it:
#   1. SELF-UPDATES: git pull the mother repo so this body always runs the latest motherboard.
#   2. ensures its own brain (compute-proxy / ClawRouter self-pay) is up on :8402.
#   3. ensures its telemetry poster is up (reports to the dashboard).
#   4. exec's the ReAct loop in the FOREGROUND — when the loop exits, this script exits, and the
#      supervisor brings the whole body back (freshly updated).
#
# The loop itself is already crash-resilient (while-true + per-wake try/catch); this wrapper adds
# OS-level persistence (survives reboots/logout) and keeps every Anicca in sync with the mother.
set -uo pipefail

REPO="${ANICCA_REPO:-$HOME/anicca}"
export ANICCA_HOME="${ANICCA_HOME:-$HOME/.anicca}"
PORT="${COMPUTE_PROXY_PORT:-8402}"
LOGDIR="$ANICCA_HOME/logs"; mkdir -p "$LOGDIR"

log() { echo "[$(date -u +%FT%TZ)] anicca-daemon: $*" >&2; }

# 1. self-update from the mother (fast-forward only; never clobber local state) ------------------
if [ -d "$REPO/.git" ]; then
  git -C "$REPO" fetch --quiet origin main 2>/dev/null \
    && git -C "$REPO" merge --ff-only origin/main 2>/dev/null \
    && log "self-updated to $(git -C "$REPO" rev-parse --short HEAD)" \
    || log "self-update skipped (offline or diverged)"
fi
# keep proxy deps present (no-op once installed)
( cd "$REPO/runtime/compute-proxy" && npm install --silent --no-audit --no-fund >/dev/null 2>&1 ) || true

# 2. brain: start the self-pay compute proxy if it is not already answering ----------------------
if ! curl -sf "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1; then
  log "starting compute-proxy on :$PORT"
  COMPUTE_PROXY_PORT="$PORT" node "$REPO/runtime/compute-proxy/proxy.mjs" >>"$LOGDIR/proxy.log" 2>&1 &
  for _ in $(seq 1 20); do curl -sf "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1 && break; sleep 0.5; done
fi

# 3. telemetry poster: one instance (kill any stale one first so the dashboard never doubles) -----
pkill -f "dashboard/telemetry-poster.mjs" 2>/dev/null || true
sleep 1
node "$REPO/runtime/dashboard/telemetry-poster.mjs" >>"$LOGDIR/poster.log" 2>&1 &

# 4. brain endpoint + model the loop should use -------------------------------------------------
export OPENAI_BASE_URL="http://127.0.0.1:$PORT/v1"
export OPENAI_API_KEY="${OPENAI_API_KEY:-x402-local}"
export ANICCA_WALLET_ADDRESS="${ANICCA_WALLET_ADDRESS:-$(node -e 'try{const w=JSON.parse(require("fs").readFileSync(process.env.HOME+"/.automaton/wallet.json"));console.log(w.address||"")}catch{process.exit(0)}')}"

log "exec loop (model tiers from config; funded=$(node -e 'import("'"$REPO"'/runtime/loop/config.mjs").then(m=>console.log(m.loadConfig(process.env,"").ANICCA_FUNDED_MODEL)).catch(()=>console.log("?"))' 2>/dev/null))"
# 5. run the loop in the foreground — its exit (crash/shutdown) ends this script; supervisor restarts.
exec node "$REPO/runtime/loop/index.mjs"
