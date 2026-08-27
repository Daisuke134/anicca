#!/usr/bin/env bash
# Reddit daily-driver healthcheck. It never creates a resident agent; it recovers a stale daily
# heartbeat by kickstarting the existing bounded launchd pass.
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

RUN_AGENT="$HOME/anicca/skills/earn/marketing-engine/run_agent.sh"
if [ "${AGENT_WIRING_PROBE_ONLY:-0}" = "1" ]; then
  printf '{"task_class":"tool-agent","runner":"%s"}\n' "$RUN_AGENT"
  exit 0
fi

LEGACY_SOCK="/tmp/anicca-reddit-loop-tmux.sock"
LEGACY_SESSION="anicca-reddit-loop"
DAILY_LABEL="ai.anicca.hf-reddit-loop-daily"
DAILY="$HOME/profitable-claude/skills/reddit/reddit-loop-daily.sh"
HB="$HOME/.openclaw/state/.reddit-loop-last-pass"
LOG="$HOME/.openclaw/logs/reddit-loop-healthcheck.log"
STALE_MIN=1560
DOMAIN="gui/$(id -u)"
DAILY_PLIST="$HOME/Library/LaunchAgents/${DAILY_LABEL}.plist"
LOCK_DIR="/tmp/.reddit-loop-healthcheck.lock"
mkdir -p "$(dirname "$LOG")" "$HOME/.openclaw/state"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then exit 0; fi
trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT

if tmux -S "$LEGACY_SOCK" has-session -t "$LEGACY_SESSION" 2>/dev/null; then
  tmux -S "$LEGACY_SOCK" kill-session -t "$LEGACY_SESSION" 2>/dev/null || true
  echo "$(date '+%F %T') retired legacy resident reddit core" >> "$LOG"
fi

age_min=999999
if [ -f "$HB" ]; then
  age_min=$(( ($(date +%s) - $(stat -f %m "$HB")) / 60 ))
fi
if [ "$age_min" -lt "$STALE_MIN" ]; then
  echo "$(date '+%F %T') reddit daily heartbeat fresh (${age_min}min)" >> "$LOG"
  exit 0
fi

ensure_daily_loaded() {
  if launchctl print "$DOMAIN/$DAILY_LABEL" >/dev/null 2>&1; then
    return 0
  fi
  if [ ! -f "$DAILY_PLIST" ]; then
    return 1
  fi
  launchctl bootstrap "$DOMAIN" "$DAILY_PLIST" >/dev/null 2>&1 || \
    launchctl load "$DAILY_PLIST" >/dev/null 2>&1 || true
  launchctl print "$DOMAIN/$DAILY_LABEL" >/dev/null 2>&1
}

if ensure_daily_loaded; then
  launchctl kickstart -k "$DOMAIN/$DAILY_LABEL"
  echo "$(date '+%F %T') reddit heartbeat stale/missing → bootstrapped/kickstarted bounded daily driver" >> "$LOG"
else
  nohup bash "$DAILY" >> "$LOG" 2>&1 &
  echo "$(date '+%F %T') reddit launchd missing → bounded recovery pid=$!" >> "$LOG"
fi
