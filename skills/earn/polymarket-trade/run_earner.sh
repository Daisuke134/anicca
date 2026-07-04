#!/usr/bin/env bash
# Polymarket no-human earner loop: bundle-arb hunt + market-making refresh.
# Runs one pass; schedule via launchd/cron every ~10min for continuous earning.
set -uo pipefail
VENV="/Users/operator/.anicca-founder/agents/polymarket-agent/.venv-pysdk/bin/python"
DIR="/Users/operator/anicca/skills/earn/polymarket-trade"
LOG="$DIR/earner.log"
ts(){ date -u +%Y-%m-%dT%H:%M:%SZ; }
echo "[$(ts)] === earner pass ===" >> "$LOG"
timeout 170 "$VENV" "$DIR/bundle_arb.py"   >> "$LOG" 2>&1 || echo "[$(ts)] bundle_arb exit $?" >> "$LOG"
timeout 170 "$VENV" "$DIR/market_maker.py" >> "$LOG" 2>&1 || echo "[$(ts)] market_maker exit $?" >> "$LOG"
echo "[$(ts)] === pass done ===" >> "$LOG"
