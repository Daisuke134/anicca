#!/bin/bash
# anicca-schedule-template entrypoint — fill empty days from a default
# template anchored at profile.alarm.wakeTime.
set -uo pipefail
SKILL="$HOME/.openclaw/skills/anicca-schedule-template"
LOG="$SKILL/state/run.log"
mkdir -p "$SKILL/state"
set -a; source "$HOME/.openclaw/.env" 2>/dev/null; set +a
echo "=== schedule-template run $(date '+%Y-%m-%d %H:%M:%S %Z') ===" >> "$LOG"
/opt/homebrew/bin/timeout --kill-after=10 180 /opt/homebrew/bin/python3 \
  "$SKILL/scripts/template.py" "$@" >> "$LOG" 2>&1
echo "exit=$?" >> "$LOG"
