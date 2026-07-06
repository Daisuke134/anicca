#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"  # launchd has a minimal PATH; tmux/python3/node/claude live in homebrew
# v2 (2026-07-04, タスク#7): pkill-by-name + backoff, ported from gig-healthcheck.sh —
# see clip-healthcheck.sh for the full incident writeup (tmux socket loss → duplicate
# cores → Load Avg 8.99 across 4 loops, real occurrence confirmed via `ps aux`).
# v4 (2026-07-04, self-heal-harness spec): mkdir atomic lock so overlapping healthcheck
# runs can't race each other's DEAD→restart sequence — see clip-healthcheck.sh for detail.
# v5 (2026-07-04, self-heal-harness spec): STALE detection (ported from gig-healthcheck.sh
# via clip-healthcheck.sh). bounty cron runs once daily, so STALE_MIN=1560 (26h).
set -uo pipefail
SOCK="/tmp/anicca-bounty-tmux.sock"; SESSION="anicca-bounty-core"
HB="$HOME/.openclaw/state/.bounty-core-last-pass"; START="$HOME/.openclaw/state/.bounty-core-last-start"; STALE_MIN=1560
LOG="$HOME/.openclaw/logs/bounty-core-healthcheck.log"; mkdir -p "$(dirname "$LOG")"
RESTART_LOG="$HOME/.openclaw/state/.bounty-core-restart-log"

LOCK_DIR="/tmp/.bounty-healthcheck.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  exit 0
fi
trap 'rmdir "$LOCK_DIR" 2>/dev/null' EXIT

restart() {
  mkdir -p "$HOME/.openclaw/state"
  local now; now=$(date +%s)
  local count=0
  if [ -f "$RESTART_LOG" ]; then
    while IFS= read -r ts; do
      [ -n "$ts" ] && [ $(( now - ts )) -le 3600 ] && count=$(( count + 1 ))
    done < "$RESTART_LOG"
  fi
  if [ "$count" -ge 5 ]; then
    echo "$(date '+%F %T') backoff: $count restarts in last 60min — not restarting" >> "$LOG"
    local task_file="$HOME/.openclaw/state/.bounty-core-selfheal-request.json"
    if [ ! -f "$task_file" ] || [ "$(( $(date +%s) - $(stat -f %m "$task_file" 2>/dev/null || echo 0) ))" -gt 3600 ]; then
      printf '{"loop":"bounty","ts":"%s","reason":"%s","restarts_last_60min":%d,"note":"healthcheck gave up restarting this loop after repeated failures. Read this on your next wake: diagnose the root cause yourself, fix the code if you can, verify the fix works, then delete this file. If you cannot fix it yourself, invoke self/issue-dev to file a GitHub issue on the mother repo instead."}\n' \
        "$(date -u +%FT%TZ)" "${1:-unknown}" "$count" > "$task_file" 2>/dev/null
    fi
    return
  fi
  echo "$now" >> "$RESTART_LOG"
  pkill -f "claude --name $SESSION" 2>/dev/null || true
  pkill -f "tmux -S $SOCK new-session" 2>/dev/null || true
  sleep 1
  echo "$(date '+%F %T') ${1:-bounty-core DEAD} → restart" >> "$LOG"
  bash "$HOME/anicca/skills/human-funded/bounty/bounty-cli.sh" --restart >> "$LOG" 2>&1 || true
}

if ! tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then
  restart "bounty-core DEAD"
elif [ ! -f "$HB" ]; then
  if [ ! -f "$START" ]; then
    # $START marker itself missing (e.g. wiped by external cleanup). Both "now" and epoch-0
    # fallbacks caused real incidents (now = STALE detection permanently disabled; epoch-0 =
    # immediate false restart of a healthy session). Don't guess: reseed the marker now and
    # let the NEXT healthcheck pass (5min later) measure from a real timestamp.
    touch "$START"
    echo "$(date '+%F %T') bounty-core: .last-start marker missing -- reseeded now, will re-check next pass" >> "$LOG"
  else
    START_MTIME="$(stat -f %m "$START")"
    START_AGE="$(( ($(date +%s) - START_MTIME) / 60 ))"
    if [ "$START_AGE" -ge "$STALE_MIN" ]; then
      restart "bounty-core ALIVE but no completed pass in >=${START_AGE}min since start (never fired)"
    else
      echo "$(date '+%F %T') bounty-core ALIVE (first pass pending, ${START_AGE}min since start)" >> "$LOG"
    fi
  fi
elif [ -f "$START" ] && [ "$(stat -f %m "$START")" -gt "$(stat -f %m "$HB")" ]; then
  # A restart happened AFTER the last completed pass (HB is from an old pass, START is fresh).
  # Must grace this like the "$HB missing" branch above, using START's age -- NOT HB's. HB's age
  # alone never resets on restart, so without this branch STALE fires on every 5min healthcheck
  # tick forever once any pass has ever completed, killing every freshly-restarted session before
  # it can ever finish a pass (clone+fix+PR takes far longer than 5min). This is the same bug
  # documented in gig-healthcheck.sh's 2026-07-05->07-06 incident writeup, ported here after it
  # produced the identical crash-restart loop for bounty-core (49h+, selfheal-request filed).
  START_AGE="$(( ($(date +%s) - $(stat -f %m "$START")) / 60 ))"
  if [ "$START_AGE" -ge "$STALE_MIN" ]; then
    restart "bounty-core STALE since restart (no completed pass in >=${START_AGE}min since last restart)"
  else
    echo "$(date '+%F %T') bounty-core ALIVE (pass pending since restart, ${START_AGE}min since restart)" >> "$LOG"
  fi
elif [ "$(( ($(date +%s) - $(stat -f %m "$HB")) / 60 ))" -ge "$STALE_MIN" ]; then
  restart "bounty-core STALE (no pass in >=${STALE_MIN}min; in-session cron likely stopped)"
else
  echo "$(date '+%F %T') bounty-core ALIVE+fresh" >> "$LOG"
fi
