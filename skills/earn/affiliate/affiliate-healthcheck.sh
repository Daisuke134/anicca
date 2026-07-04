#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"  # launchd has a minimal PATH; tmux/python3/node/claude live in homebrew
# v2 (2026-07-04, タスク#7): pkill-by-name + backoff, ported from gig-healthcheck.sh —
# see clip-healthcheck.sh for the full incident writeup (tmux socket loss → duplicate
# cores → Load Avg 8.99 across 4 loops, real occurrence confirmed via `ps aux`).
# v4 (2026-07-04, self-heal-harness spec): mkdir atomic lock so overlapping healthcheck
# runs can't race each other's DEAD→restart sequence — see clip-healthcheck.sh for detail.
# v5 (2026-07-04, self-heal-harness spec): STALE detection (ported from gig-healthcheck.sh
# via clip-healthcheck.sh). affiliate cron runs once daily, so STALE_MIN=1560 (26h) —
# long enough that a single day's normal cron cadence never false-triggers.
set -uo pipefail
SOCK="/tmp/anicca-affiliate-tmux.sock"; SESSION="anicca-affiliate-core"
HB="$HOME/.openclaw/state/.affiliate-core-last-pass"; START="$HOME/.openclaw/state/.affiliate-core-last-start"; STALE_MIN=1560
LOG="$HOME/.openclaw/logs/affiliate-core-healthcheck.log"; mkdir -p "$(dirname "$LOG")"
RESTART_LOG="$HOME/.openclaw/state/.affiliate-core-restart-log"

LOCK_DIR="/tmp/.affiliate-healthcheck.lock"
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
    return
  fi
  echo "$now" >> "$RESTART_LOG"
  pkill -f "claude --name $SESSION" 2>/dev/null || true
  pkill -f "tmux -S $SOCK new-session" 2>/dev/null || true
  sleep 1
  echo "$(date '+%F %T') ${1:-affiliate-core DEAD} → restart" >> "$LOG"
  bash "$HOME/anicca/skills/earn/affiliate/affiliate-cli.sh" --restart >> "$LOG" 2>&1 || true
}

if ! tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then
  restart "affiliate-core DEAD"
elif [ ! -f "$HB" ]; then
  START_MTIME="$(stat -f %m "$START" 2>/dev/null || date +%s)"
  START_AGE="$(( ($(date +%s) - START_MTIME) / 60 ))"
  if [ "$START_AGE" -ge "$STALE_MIN" ]; then
    restart "affiliate-core ALIVE but no completed pass in >=${START_AGE}min since start (never fired)"
  else
    echo "$(date '+%F %T') affiliate-core ALIVE (first pass pending, ${START_AGE}min since start)" >> "$LOG"
  fi
elif [ "$(( ($(date +%s) - $(stat -f %m "$HB" 2>/dev/null || date +%s)) / 60 ))" -ge "$STALE_MIN" ]; then
  restart "affiliate-core STALE (no pass in >=${STALE_MIN}min; in-session cron likely stopped)"
else
  echo "$(date '+%F %T') affiliate-core ALIVE+fresh" >> "$LOG"
fi
