#!/usr/bin/env bash
# Detached wrapper for kpi-dashboard.
# Usage: run-detached.sh [daily]
set -euo pipefail
TAG="${1:-daily}"
ROOT="$HOME/anicca-monk-factory"
TS=$(date +%Y%m%d_%H%M%S)
LOG="$ROOT/state/kpi_${TAG}_${TS}.log"
mkdir -p "$ROOT/state"

nohup bash "$HOME/.openclaw/skills/kpi-dashboard/scripts/run.sh" "$TAG" \
  > "$LOG" 2>&1 < /dev/null &
PID=$!
disown $PID 2>/dev/null || true

echo "✅ kpi-dashboard kicked off PID=$PID tag=$TAG"
echo "   log: $LOG"
