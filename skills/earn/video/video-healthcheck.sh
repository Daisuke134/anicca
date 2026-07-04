#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"  # launchd has a minimal PATH; tmux/python3/node/claude live in homebrew
# video-healthcheck.sh — OS-level supervisor (launchd, every 5min). If the always-on video-core
# tmux session is dead, restart it. Cloned from clip-healthcheck.sh so video is a real loop too.
#
# v2 (2026-07-04, タスク#7): pkill-by-name + backoff, ported from gig-healthcheck.sh —
# see clip-healthcheck.sh for the full incident writeup (tmux socket loss → duplicate
# cores → Load Avg 8.99 across 4 loops, real occurrence confirmed via `ps aux`).
# v4 (2026-07-04, self-heal-harness spec): mkdir atomic lock so overlapping healthcheck
# runs can't race each other's DEAD→restart sequence — see clip-healthcheck.sh for detail.
# v5 (2026-07-04, self-heal-harness spec): STALE detection (ported from gig-healthcheck.sh
# via clip-healthcheck.sh). video cron runs every 4h, so STALE_MIN=360 (6h, 1.5x cadence).
set -uo pipefail
SOCK="/tmp/anicca-video-tmux.sock"; SESSION="anicca-video-core"
HB="$HOME/.openclaw/state/.video-core-last-pass"; START="$HOME/.openclaw/state/.video-core-last-start"; STALE_MIN=360
LOG="$HOME/.openclaw/logs/video-core-healthcheck.log"; mkdir -p "$(dirname "$LOG")"
RESTART_LOG="$HOME/.openclaw/state/.video-core-restart-log"

LOCK_DIR="/tmp/.video-healthcheck.lock"
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
  echo "$(date '+%F %T') ${1:-video-core DEAD} → restarting" >> "$LOG"
  bash "$HOME/anicca/skills/earn/video/video-cli.sh" --restart >> "$LOG" 2>&1 || true
}

if ! tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then
  restart "video-core DEAD"
elif [ ! -f "$HB" ]; then
  START_MTIME="$(stat -f %m "$START" 2>/dev/null || date +%s)"
  START_AGE="$(( ($(date +%s) - START_MTIME) / 60 ))"
  if [ "$START_AGE" -ge "$STALE_MIN" ]; then
    restart "video-core ALIVE but no completed pass in >=${START_AGE}min since start (never fired)"
  else
    echo "$(date '+%F %T') video-core ALIVE (first pass pending, ${START_AGE}min since start)" >> "$LOG"
  fi
elif [ "$(( ($(date +%s) - $(stat -f %m "$HB" 2>/dev/null || date +%s)) / 60 ))" -ge "$STALE_MIN" ]; then
  restart "video-core STALE (no pass in >=${STALE_MIN}min; in-session cron likely stopped)"
else
  echo "$(date '+%F %T') video-core ALIVE+fresh" >> "$LOG"
fi
