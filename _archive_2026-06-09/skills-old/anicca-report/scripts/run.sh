#!/bin/bash
# anicca-report entrypoint — mail the day's summary.
set -uo pipefail
SKILL="$HOME/.openclaw/skills/anicca-report"
LOG="$SKILL/state/run.log"
mkdir -p "$SKILL/state"
set -a; source "$HOME/.openclaw/.env" 2>/dev/null; set +a
echo "=== anicca-report run $(date '+%Y-%m-%d %H:%M:%S %Z') ===" >> "$LOG"
/opt/homebrew/bin/timeout --kill-after=10 120 /opt/homebrew/bin/python3 \
  "$SKILL/scripts/report.py" "$@" >> "$LOG" 2>&1
echo "exit=$?" >> "$LOG"
