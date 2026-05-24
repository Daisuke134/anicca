#!/usr/bin/env bash
# Detached wrapper for copy-viral-format-factory.
# Usage:
#   run-detached.sh weekly                       (rotates niches_queue.txt)
#   run-detached.sh ondemand "<niche>" "<lang>"
set -euo pipefail
MODE="${1:-weekly}"
NICHE="${2:-}"
LANG_ARG="${3:-en}"

ROOT="$HOME/anicca-monk-factory"
TS=$(date +%Y%m%d_%H%M%S)
LOG="$ROOT/state/virality_${MODE}_${TS}.log"
mkdir -p "$ROOT/state"

nohup bash "$HOME/.openclaw/skills/copy-viral-format-factory/scripts/run.sh" "$MODE" "$NICHE" "$LANG_ARG" \
  > "$LOG" 2>&1 < /dev/null &
PID=$!
disown $PID 2>/dev/null || true

echo "✅ copy-viral-format-factory kicked off PID=$PID mode=$MODE niche=$NICHE lang=$LANG_ARG"
echo "   log: $LOG"
