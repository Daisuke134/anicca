#!/usr/bin/env bash
# Detached wrapper for daily-letter-sender.
set -euo pipefail
TAG="${1:-daily}"
ROOT="$HOME/anicca-monk-factory"
TS=$(date +%Y%m%d_%H%M%S)
LOG="$ROOT/state/letter_send_${TS}.log"
mkdir -p "$ROOT/state"

nohup bash "$HOME/.openclaw/skills/daily-letter-sender/scripts/run.sh" "$TAG" \
  > "$LOG" 2>&1 < /dev/null &
PID=$!
disown $PID 2>/dev/null || true

echo "✅ daily-letter-sender kicked off PID=$PID tag=$TAG"
echo "   log: $LOG"
