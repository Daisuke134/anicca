#!/bin/bash
# anicca-travel-fill entrypoint — scans gcal + inserts 🚆 移動 blocks where
# adjacent events have different locations.
set -uo pipefail
SKILL="$HOME/.openclaw/skills/anicca-travel-fill"
LOG="$SKILL/state/run.log"
mkdir -p "$SKILL/state"
set -a; source "$HOME/.openclaw/.env" 2>/dev/null; set +a
echo "=== travel-fill run $(date '+%Y-%m-%d %H:%M:%S %Z') ===" >> "$LOG"
/opt/homebrew/bin/timeout --kill-after=10 180 /opt/homebrew/bin/python3 \
  "$SKILL/scripts/travel_fill.py" "$@" >> "$LOG" 2>&1
echo "exit=$?" >> "$LOG"
