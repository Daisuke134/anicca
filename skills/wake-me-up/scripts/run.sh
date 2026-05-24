#!/bin/bash
# Single mini-proof entrypoint for the wake-me-up cron.
# The cron agent only has to run THIS one command — no decisions.
# Ensures the realtime bridge, then runs the re-call-until-awake loop.
# Falls back to the scripted call only if the bridge cannot come up.
set -uo pipefail

# Phone/name come from the per-user profile unless passed explicitly (OSS-general).
PROF="$HOME/.openclaw/identity/profile.json"
PHONE="${1:-$(python3 -c "import json;p=json.load(open('$PROF'));print(p['contact']['phone'])" 2>/dev/null)}"
NAME="${2:-$(python3 -c "import json;p=json.load(open('$PROF'));i=p['identity'];print(i.get('preferredName') or i.get('{{profile.lateness.stakeholders.senderType}}Name',''))" 2>/dev/null)}"
SKILL="$HOME/.openclaw/skills/wake-me-up"
LOG_DIR="$SKILL/state"
LOG="$LOG_DIR/run.log"
mkdir -p "$LOG_DIR"

echo "=== wake run $(date '+%Y-%m-%d %H:%M:%S %Z') phone=$PHONE name=$NAME ===" >> "$LOG"

if bash "$SKILL/scripts/ensure-bridge.sh" >> "$LOG" 2>&1; then
  python3 "$SKILL/scripts/wake_loop.py" "$PHONE" "$NAME" >> "$LOG" 2>&1
  rc=$?
  echo "wake_loop exit=$rc" >> "$LOG"
  exit $rc
else
  echo "ensure-bridge FAILED -> scripted fallback" >> "$LOG"
  python3 "$HOME/.openclaw/workspace/wake-up/twilio_wake_call.py" "$PHONE" "$NAME" >> "$LOG" 2>&1
  exit $?
fi
