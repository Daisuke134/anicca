#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"  # launchd has a minimal PATH; tmux/python3/node/claude live in homebrew
# gig-healthcheck.sh — launchd supervisor (5min). Two failure modes, both self-heal:
#   (1) DEAD: the tmux core died → restart it.
#   (2) STALE: the core is alive but the in-session :27 cron stopped firing (no pass in >90 min) →
#       restart it (a fresh start re-runs one pass + re-registers the cron). This closes the
#       continuity gap where the session lives but the internal scheduler silently stopped, so the
#       loop never wakes to reply to a buyer / catch a 仮払い. Heartbeat = ~/gig/.last-pass, touched
#       by the core at the start of every pass (see gig-cli.sh cron prompt).
#
# v2 (2026-07-04, self-heal-harness spec): mkdir atomic lock so overlapping healthcheck
# runs can't race each other's restart sequence (same pattern added to the other 4 loops'
# healthchecks — see clip-healthcheck.sh for the full writeup).
set -uo pipefail
SOCK="/tmp/anicca-gig-tmux.sock"; SESSION="anicca-gig-core"
HB="$HOME/gig/.last-pass"; START="$HOME/gig/.last-start"; STALE_MIN=90
LOG="$HOME/.openclaw/logs/gig-core-healthcheck.log"; mkdir -p "$(dirname "$LOG")"
RESTART_LOG="$HOME/gig/.restart-log"

LOCK_DIR="/tmp/.gig-healthcheck.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  exit 0
fi
trap 'rmdir "$LOCK_DIR" 2>/dev/null' EXIT

restart(){
  # backoff: max 5 restarts per 60min window (prevent subscription drain under persistent failure)
  mkdir -p "$HOME/gig"
  local now; now=$(date +%s)
  local count=0
  if [ -f "$RESTART_LOG" ]; then
    while IFS= read -r ts; do
      [ -n "$ts" ] && [ $(( now - ts )) -le 3600 ] && count=$(( count + 1 ))
    done < "$RESTART_LOG"
  fi
  if [ "$count" -ge 5 ]; then
    echo "$(date '+%F %T') backoff: $count restarts in last 60min — not restarting (likely quota/persistent failure; will resume after reset)" >> "$LOG"
    local task_file="$HOME/.openclaw/state/.gig-core-selfheal-request.json"
    if [ ! -f "$task_file" ] || [ "$(( $(date +%s) - $(stat -f %m "$task_file" 2>/dev/null || echo 0) ))" -gt 3600 ]; then
      printf '{"loop":"gig","ts":"%s","reason":"%s","restarts_last_60min":%d,"note":"healthcheck gave up restarting this loop after repeated failures. Read this on your next wake: diagnose the root cause yourself, fix the code if you can, verify the fix works, then delete this file. If you cannot fix it yourself, invoke self/issue-dev to file a GitHub issue on the mother repo instead."}\n' \
        "$(date -u +%FT%TZ)" "${1:-unknown}" "$count" > "$task_file" 2>/dev/null
    fi
    return
  fi
  echo "$now" >> "$RESTART_LOG"
  echo "$(date '+%F %T') $1 → restarting" >> "$LOG"
  bash "$HOME/anicca/skills/human-funded/gig/gig-cli.sh" --restart >> "$LOG" 2>&1 || true
}

if ! tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then
  restart "gig-core DEAD"
elif [ ! -f "$HB" ]; then
  # .last-pass is created ONLY by a COMPLETED pass (NOT at startup — startup seeds .last-start).
  # So a missing .last-pass right after boot is normal; give a grace window since .last-start before
  # treating "never completed a pass" as a failure (else we'd kill the core mid-first-pass = restart loop).
  if [ ! -f "$START" ]; then
    # $START marker itself missing (e.g. wiped by external cleanup). An epoch-0 fallback here
    # (as this file used to have) made START_AGE ~30M minutes and triggered an immediate false
    # restart of a healthy session; a "now" fallback (as the other 5 loops' healthchecks used)
    # instead permanently disables STALE detection. Don't guess: reseed the marker now and let
    # the NEXT healthcheck pass (5min later) measure from a real timestamp.
    touch "$START"
    echo "$(date '+%F %T') gig-core: .last-start marker missing -- reseeded now, will re-check next pass" >> "$LOG"
  else
    START_AGE="$(( ($(date +%s) - $(stat -f %m "$START")) / 60 ))"
    if [ "$START_AGE" -ge "$STALE_MIN" ]; then
      restart "gig-core ALIVE but no completed pass in >=${START_AGE}min since start (never fired)"
    else
      echo "$(date '+%F %T') gig-core ALIVE (first pass pending, ${START_AGE}min since start)" >> "$LOG"
    fi
  fi
elif [ "$(( ($(date +%s) - $(stat -f %m "$HB")) / 60 ))" -ge "$STALE_MIN" ]; then
  # FIND-005: -ge to match auditor's >=90 threshold exactly
  restart "gig-core STALE (no pass in >=${STALE_MIN}min; in-session cron likely stopped)"
else
  echo "$(date '+%F %T') gig-core ALIVE+fresh" >> "$LOG"
fi
