#!/usr/bin/env bash
# Detached wrapper for winner-analyzer.
# Usage: run-detached.sh [weekly]
set -euo pipefail
TAG="${1:-weekly}"
ROOT="$HOME/anicca-monk-factory"
TS=$(date +%Y%m%d_%H%M%S)
LOG="$ROOT/state/winner_${TAG}_${TS}.log"
mkdir -p "$ROOT/state"

nohup bash "$HOME/.openclaw/skills/winner-analyzer/scripts/run.sh" "$TAG" \
  > "$LOG" 2>&1 < /dev/null &
PID=$!
disown $PID 2>/dev/null || true

echo "✅ winner-analyzer kicked off PID=$PID tag=$TAG"
echo "   log: $LOG"
