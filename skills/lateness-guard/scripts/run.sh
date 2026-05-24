#!/bin/bash
# Single mini-proof entrypoint for lateness-guard crons / heartbeat.
# Runs the lateness check (gcal departBy x live location -> call if late-risk).
# The cron agent only has to run THIS one command.
set -uo pipefail
SKILL="$HOME/.openclaw/skills/lateness-guard"
LOG="$SKILL/state/run.log"
mkdir -p "$SKILL/state"
echo "=== lateness run $(date '+%Y-%m-%d %H:%M:%S %Z') ===" >> "$LOG"
python3 "$SKILL/scripts/lateness_check.py" "$@" >> "$LOG" 2>&1
echo "exit=$?" >> "$LOG"
