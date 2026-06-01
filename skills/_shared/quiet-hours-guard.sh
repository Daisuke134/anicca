#!/bin/bash
# quiet-hours-guard.sh — exit 0 (= silent skip) if current time is in the
# operator's quiet hours window (profile.alarm.quietHoursStart..quietHoursEnd).
# Source-include this at the top of any */5 or */15 cron run.sh that should
# NOT fire while the operator is asleep:
#
#   source "$HOME/.openclaw/skills/_shared/quiet-hours-guard.sh"
#
# Reads from ~/.openclaw/identity/profile.json. Falls back to 23:30..05:30 if
# the profile is missing or malformed.
QUIET_NOW=$(python3 - <<'PY'
import json, os
from datetime import datetime
try:
    p = json.load(open(os.path.expanduser('~/.openclaw/identity/profile.json')))
    a = p.get('alarm', {})
    s = a.get('quietHoursStart', '23:30')
    e = a.get('quietHoursEnd', '05:30')
    sh, sm = (int(x) for x in s.split(':'))
    eh, em = (int(x) for x in e.split(':'))
    n = datetime.now()
    cur = n.hour * 60 + n.minute
    start, end = sh * 60 + sm, eh * 60 + em
    print(1 if (start < end and start <= cur < end) or (start >= end and (cur >= start or cur < end)) else 0)
except Exception:
    print(0)
PY
)
if [ "$QUIET_NOW" = "1" ]; then
  exit 0
fi
