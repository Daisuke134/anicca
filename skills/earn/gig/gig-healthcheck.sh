#!/usr/bin/env bash
LIFE_MANAGER_REPO="${LIFE_MANAGER_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$LIFE_MANAGER_REPO" ] || { echo "LIFE_MANAGER_REPO could not be resolved" >&2; exit 2; }
export LIFE_MANAGER_REPO
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"  # launchd has a minimal PATH; tmux/python3/node/claude live in homebrew
# gig-healthcheck.sh — launchd supervisor (5min). Two failure modes, both self-heal:
#   (1) DEAD: the tmux core died → restart it.
#   (2) STALE: the core is alive but the in-session :27 cron stopped firing (no pass in >90 min) →
#       restart it (a fresh start re-runs one pass + re-registers the cron). This closes the
#       continuity gap where the session lives but the internal scheduler silently stopped, so the
#       loop never wakes to reply to a buyer / catch a 仮払い. Heartbeat = ~/gig/.last-pass, touched
#       by the core at the start of every pass (see gig-cli.sh cron prompt).
set -uo pipefail
SOCK="/tmp/anicca-gig-tmux.sock"; SESSION="anicca-gig-core"
HB="$HOME/gig/.last-pass"; STALE_MIN=90
LOG="$HOME/.local/state/life-manager/logs/gig-core-healthcheck.log"; mkdir -p "$(dirname "$LOG")"
RESTART_LOG="$HOME/gig/.restart-log"
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
    return
  fi
  echo "$now" >> "$RESTART_LOG"
  echo "$(date '+%F %T') $1 → restarting" >> "$LOG"
  bash "$LIFE_MANAGER_REPO/skills/earn/gig/gig-cli.sh" --restart >> "$LOG" 2>&1 || true
}

if ! tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then
  restart "gig-core DEAD"
elif [ ! -f "$HB" ] || [ "$HB" -ot "$HOME/gig/.last-start" ]; then
  # .last-pass is created ONLY by a COMPLETED pass (NOT at startup — startup seeds .last-start).
  # So a missing OR stale-from-a-PRIOR-session .last-pass right after boot is normal; give a grace
  # window since .last-start before treating "never completed a pass" as a failure (else we'd kill
  # the core mid-first-pass = restart loop). The `-ot .last-start` half of this condition closes a
  # real incident (2026-07-11 gig-cadence self-fix): after a multi-day outage left .last-pass dated
  # 2026-07-08, a freshly-restarted, genuinely-working session was judged STALE on every single tick
  # (.last-pass's absolute age was always >=90min) and got killed every ~5min before any pass could
  # ever run long enough to touch .last-pass and break the cycle — an unrecoverable restart loop that
  # would have silently reproduced this same cadence miss every day going forward. Comparing against
  # .last-start (this session's own boot time, always fresh on restart) instead of trusting an
  # ancient .last-pass left over from a session that no longer exists is the fix; once a pass
  # completes, .last-pass becomes newer than .last-start and this branch stops applying, falling
  # through to the real staleness check below (which still correctly catches an in-session cron that
  # silently dies mid-lifetime, since in that case .last-pass stays NEWER than the old .last-start).
  START_AGE="$(( ($(date +%s) - $(stat -f %m "$HOME/gig/.last-start" 2>/dev/null || echo 0)) / 60 ))"
  if [ "$START_AGE" -ge "$STALE_MIN" ]; then
    restart "gig-core ALIVE but no completed pass in >=${START_AGE}min since start (never fired)"
  else
    echo "$(date '+%F %T') gig-core ALIVE (first pass pending, ${START_AGE}min since start)" >> "$LOG"
  fi
elif [ "$(( ($(date +%s) - $(stat -f %m "$HB" 2>/dev/null || echo 0)) / 60 ))" -ge "$STALE_MIN" ]; then
  # FIND-005: -ge to match auditor's >=90 threshold exactly
  restart "gig-core STALE (no pass in >=${STALE_MIN}min; in-session cron likely stopped)"
else
  echo "$(date '+%F %T') gig-core ALIVE+fresh" >> "$LOG"
fi
