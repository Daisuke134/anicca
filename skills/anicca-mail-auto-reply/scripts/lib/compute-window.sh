#!/usr/bin/env bash
# Compute WINDOW_HOURS based on time since last successful run.
# Used by run.sh to widen scan window after a missed cycle.
# Output: prints window hours integer (default 2, max 72)

set -uo pipefail
SKILL=~/.openclaw/skills/anicca-mail-auto-reply
STATE_FILE=$SKILL/state/last-run-ts.txt
DEFAULT_WINDOW=2     # 2h default
MAX_WINDOW=72        # 3 day cap (missed-run safety)

if [ ! -f "$STATE_FILE" ]; then
  echo $MAX_WINDOW
  exit 0
fi

LAST=$(cat "$STATE_FILE" 2>/dev/null || echo 0)
NOW=$(date +%s)
GAP=$(( NOW - LAST ))
GAP_H=$(( GAP / 3600 ))

# Window = max(DEFAULT, GAP*1.5) capped at MAX
WINDOW=$DEFAULT_WINDOW
if [ $GAP_H -ge 1 ]; then
  WINDOW=$(( GAP_H * 3 / 2 ))
fi
[ $WINDOW -gt $MAX_WINDOW ] && WINDOW=$MAX_WINDOW
[ $WINDOW -lt $DEFAULT_WINDOW ] && WINDOW=$DEFAULT_WINDOW
echo $WINDOW
