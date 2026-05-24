#!/usr/bin/env bash
# Detached wrapper for weekly-fresh-letter.
set -euo pipefail
TAG="${1:-weekly}"
ROOT="$HOME/anicca-monk-factory"
TS=$(date +%Y%m%d_%H%M%S)
LOG="$ROOT/state/weekly_fresh_${TS}.log"
mkdir -p "$ROOT/state"

nohup bash "$HOME/.openclaw/skills/weekly-fresh-letter/scripts/run.sh" "$TAG" \
  > "$LOG" 2>&1 < /dev/null &
PID=$!
disown $PID 2>/dev/null || true

echo "✅ weekly-fresh-letter kicked off PID=$PID tag=$TAG"
echo "   log: $LOG"
