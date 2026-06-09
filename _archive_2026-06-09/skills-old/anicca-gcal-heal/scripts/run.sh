#!/bin/bash
# anicca-gcal-heal entrypoint — PATCH empty event.location fields.
set -uo pipefail
SKILL="$HOME/.openclaw/skills/anicca-gcal-heal"
LOG="$SKILL/state/run.log"
mkdir -p "$SKILL/state"
set -a; source "$HOME/.openclaw/.env" 2>/dev/null; set +a
echo "=== gcal-heal run $(date '+%Y-%m-%d %H:%M:%S %Z') ===" >> "$LOG"
/opt/homebrew/bin/timeout --kill-after=10 180 /opt/homebrew/bin/python3 \
  "$SKILL/scripts/gcal_heal.py" "$@" >> "$LOG" 2>&1
echo "exit=$?" >> "$LOG"
