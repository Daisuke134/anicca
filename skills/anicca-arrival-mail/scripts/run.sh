#!/bin/bash
# anicca-arrival-mail entrypoint — send "I'm here" mail when arrival detected.
set -uo pipefail
SKILL="$HOME/.openclaw/skills/anicca-arrival-mail"
LOG="$SKILL/state/run.log"
mkdir -p "$SKILL/state"
set -a; source "$HOME/.openclaw/.env" 2>/dev/null; set +a
echo "=== arrival-mail run $(date '+%Y-%m-%d %H:%M:%S %Z') ===" >> "$LOG"
/opt/homebrew/bin/timeout --kill-after=10 60 /opt/homebrew/bin/python3 \
  "$SKILL/scripts/arrival.py" "$@" >> "$LOG" 2>&1
echo "exit=$?" >> "$LOG"
