#!/usr/bin/env bash
# Polymarket no-human earner loop: bundle-arb hunt + market-making refresh.
# Runs one pass; schedule via launchd/cron every ~10min for continuous earning.
set -uo pipefail
VENV="/Users/anicca/.anicca-founder/agents/polymarket-agent/.venv-pysdk/bin/python"
DIR="/Users/anicca/anicca/skills/earn/polymarket-trade"
LOG="$DIR/earner.log"
ts(){ date -u +%Y-%m-%dT%H:%M:%SZ; }
TO="$(command -v gtimeout || command -v timeout || true)"
run(){ if [ -n "$TO" ]; then "$TO" 200 "$@"; else "$@"; fi; }  # python has its own net timeouts
echo "[$(ts)] === earner pass ===" >> "$LOG"
run "$VENV" "$DIR/bundle_arb.py"   >> "$LOG" 2>&1 || echo "[$(ts)] bundle_arb exit $?" >> "$LOG"
run "$VENV" "$DIR/market_maker.py" >> "$LOG" 2>&1 || echo "[$(ts)] market_maker exit $?" >> "$LOG"
echo "[$(ts)] === pass done ===" >> "$LOG"
