#!/usr/bin/env bash
# Polymarket no-human earner loop: bundle-arb hunt + market-making refresh.
# Runs one pass; schedule via launchd/cron every ~10min for continuous earning.
set -uo pipefail
# launchd gives a bare PATH (/usr/bin:/bin) with no node/gtimeout → telemetry POST silently
# failed and dropped claude-p off the dashboard (recurring #17). Set a portable PATH here so it
# works under launchd on any machine (homebrew on Apple Silicon, /usr/local on Intel, /usr on Linux).
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
VENV="/Users/operator/.anicca-founder/agents/polymarket-agent/.venv-pysdk/bin/python"
DIR="/Users/operator/anicca/skills/earn/polymarket-trade"
LOG="$DIR/earner.log"
ts(){ date -u +%Y-%m-%dT%H:%M:%SZ; }
TO="$(command -v gtimeout || command -v timeout || true)"
run(){ if [ -n "$TO" ]; then "$TO" 200 "$@"; else "$@"; fi; }  # python has its own net timeouts
echo "[$(ts)] === earner pass ===" >> "$LOG"
run "$VENV" "$DIR/bundle_arb.py"   >> "$LOG" 2>&1 || echo "[$(ts)] bundle_arb exit $?" >> "$LOG"
run "$VENV" "$DIR/market_maker.py" >> "$LOG" 2>&1 || echo "[$(ts)] market_maker exit $?" >> "$LOG"
echo "[$(ts)] === pass done ===" >> "$LOG"

# Signed telemetry POST (#25 TELEM) — fail-safe: never affects the trading passes above.
# use run() helper (gtimeout/timeout/none): mac has no bare `timeout`, so a direct call is
# command-not-found under launchd and silently drops claude-p off the dashboard (recurring #17).
run node /Users/operator/anicca/runtime/dashboard/telemetry-post-claude-p.mjs >> "$DIR/telemetry-post.log" 2>&1 || true
