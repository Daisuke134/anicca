#!/usr/bin/env bash
LIFE_MANAGER_REPO="${LIFE_MANAGER_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$LIFE_MANAGER_REPO" ] || { echo "LIFE_MANAGER_REPO could not be resolved" >&2; exit 2; }
export LIFE_MANAGER_REPO
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
HB="$HOME/.local/state/life-manager/state/.video-core-last-pass"; START="$HOME/.local/state/life-manager/state/.video-core-last-start"; STALE_MIN=360
LOG="$HOME/.local/state/life-manager/logs/video-core-healthcheck.log"; mkdir -p "$(dirname "$LOG")"
RESTART_LOG="$HOME/.local/state/life-manager/state/.video-core-restart-log"

LOCK_DIR="/tmp/.video-healthcheck.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  exit 0
fi
trap 'rmdir "$LOCK_DIR" 2>/dev/null' EXIT

restart() {
  mkdir -p "$HOME/.local/state/life-manager/state"
  local now; now=$(date +%s)
  local count=0
  if [ -f "$RESTART_LOG" ]; then
    while IFS= read -r ts; do
      [ -n "$ts" ] && [ $(( now - ts )) -le 3600 ] && count=$(( count + 1 ))
    done < "$RESTART_LOG"
  fi
  if [ "$count" -ge 5 ]; then
    echo "$(date '+%F %T') backoff: $count restarts in last 60min — not restarting" >> "$LOG"
    local task_file="$HOME/.local/state/life-manager/state/.video-core-selfheal-request.json"
    if [ ! -f "$task_file" ] || [ "$(( $(date +%s) - $(stat -f %m "$task_file" 2>/dev/null || echo 0) ))" -gt 3600 ]; then
      printf '{"loop":"video","ts":"%s","reason":"%s","restarts_last_60min":%d,"note":"healthcheck gave up restarting this loop after repeated failures. Read this on your next wake: diagnose the root cause yourself, fix the code if you can, verify the fix works, then delete this file. If you cannot fix it yourself, invoke self/issue-dev to file a GitHub issue on the mother repo instead."}\n' \
        "$(date -u +%FT%TZ)" "${1:-unknown}" "$count" > "$task_file" 2>/dev/null
    fi
    return
  fi
  echo "$now" >> "$RESTART_LOG"
  pkill -f "claude --name $SESSION" 2>/dev/null || true
  pkill -f "tmux -S $SOCK new-session" 2>/dev/null || true
  sleep 1
  echo "$(date '+%F %T') ${1:-video-core DEAD} → restarting" >> "$LOG"
  bash "$LIFE_MANAGER_REPO/skills/earn/video/video-cli.sh" --restart >> "$LOG" 2>&1 || true
}

if ! tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then
  restart "video-core DEAD"
else
  if [ ! -f "$START" ]; then
    # $START marker itself missing (e.g. wiped by external cleanup). Both "now" and epoch-0
    # fallbacks caused real incidents (now = STALE detection permanently disabled; epoch-0 =
    # immediate false restart of a healthy session). Don't guess: reseed the marker now and
    # let the NEXT healthcheck pass (5min later) measure from a real timestamp.
    touch "$START"
    echo "$(date '+%F %T') video-core: .last-start marker missing -- reseeded now, will re-check next pass" >> "$LOG"
  else
    # REF = the more recent of "last completed pass" and "last restart". Comparing against
    # $HB alone is wrong: a fresh restart never touches $HB (only $START), so once $HB goes
    # stale once it stays stale across every future restart -- the very next healthcheck tick
    # (5min later) would see an ancient $HB and kill the brand-new session again, before a
    # real pass (browser warmup + video gen + post + on-chain confirm) can finish. Real
    # incident: 2026-07-06 04:33 -> 18:42, 14h crash loop, 40+ restarts, zero completed passes.
    # Anchoring on max($HB, $START) gives every fresh restart its own full $STALE_MIN grace
    # window, while still killing a session that goes stale again after that grace expires.
    HB_MTIME=0
    [ -f "$HB" ] && HB_MTIME="$(stat -f %m "$HB")"
    START_MTIME="$(stat -f %m "$START")"
    REF_MTIME=$HB_MTIME
    [ "$START_MTIME" -gt "$REF_MTIME" ] && REF_MTIME=$START_MTIME
    AGE_MIN="$(( ($(date +%s) - REF_MTIME) / 60 ))"
    if [ "$AGE_MIN" -ge "$STALE_MIN" ]; then
      restart "video-core STALE (no pass in >=${AGE_MIN}min since last start/pass; in-session cron likely stopped)"
    else
      echo "$(date '+%F %T') video-core ALIVE (last pass/start ${AGE_MIN}min ago)" >> "$LOG"
    fi
  fi
fi
