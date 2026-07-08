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
# EARN-2 (#14): autonomously collect any RESOLVED winning positions FIRST, so the freed cash is
# available to the market-making pass below. redeem.py is idempotent (no-op when nothing is
# redeemable), so the loop — not a human — collects every future win. This replaces the one-time
# manual redeem (EARN-1) with the agent doing it itself each pass.
run "$VENV" "$DIR/redeem.py"       >> "$LOG" 2>&1 || echo "[$(ts)] redeem exit $?" >> "$LOG"
# money-safety guard (fix: broken fail-closed): redeem.py::check_cumulative_halt() writes KILL when
# cumulative net_usdc < reserve. run.sh honored KILL but this launchd entrypoint did NOT, so the
# valve was dead in production. redeem above still runs (collects wins, reduces exposure); if halted,
# skip the new-risk trading passes below.
if [ -f "$DIR/KILL" ]; then
  echo "[$(ts)] KILL present — cumulative-loss guard: skipping bundle_arb/market_maker" >> "$LOG"
  exit 0
fi
run "$VENV" "$DIR/bundle_arb.py"   >> "$LOG" 2>&1 || echo "[$(ts)] bundle_arb exit $?" >> "$LOG"
run "$VENV" "$DIR/market_maker.py" >> "$LOG" 2>&1 || echo "[$(ts)] market_maker exit $?" >> "$LOG"
echo "[$(ts)] === pass done ===" >> "$LOG"

# Signed telemetry POST (#25 TELEM) — fail-safe: never affects the trading passes above.
# use run() helper (gtimeout/timeout/none): mac has no bare `timeout`, so a direct call is
# command-not-found under launchd and silently drops claude-p off the dashboard (recurring #17).
run node /Users/operator/anicca/runtime/dashboard/telemetry-post-claude-p.mjs >> "$DIR/telemetry-post.log" 2>&1 || true
