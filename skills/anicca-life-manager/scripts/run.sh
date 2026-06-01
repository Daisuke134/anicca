#!/bin/bash
# anicca-life-manager 5-min heartbeat entrypoint.
# Deterministic: gcal departBy x Telegram Live Location -> call if late-risk.
# Invoked by openclaw cron b2bf06ee (dais-lateness-heartbeat) every 5 min, 0-23 JST.
set -uo pipefail
SKILL="$HOME/.openclaw/skills/anicca-life-manager"
LOG="$SKILL/state/run.log"
mkdir -p "$SKILL/state"
# Load env: GOOGLE_API_KEY, TWILIO_*, ANICCA_PHONE_DIALOUT_URL, GOG_*
set -a; source "$HOME/.openclaw/.env" 2>/dev/null; set +a
export ANICCA_PHONE_DIALOUT_URL="${ANICCA_PHONE_DIALOUT_URL:-http://127.0.0.1:7860}"
echo "=== lateness run $(date '+%Y-%m-%d %H:%M:%S %Z') ===" >> "$LOG"
/opt/homebrew/bin/timeout --kill-after=10 110 /opt/homebrew/bin/python3 \
  "$SKILL/scripts/lateness_check.py" "$@" >> "$LOG" 2>&1
echo "exit=$?" >> "$LOG"
