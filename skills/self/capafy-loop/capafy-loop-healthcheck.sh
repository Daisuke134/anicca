#!/usr/bin/env bash
# Supervise the single launchd-owned Capafy daily pass. Do not create a second
# tmux/Claude scheduler: ai.anicca.capafy-loop-daily is the only execution owner.
set -uo pipefail

LABEL="ai.anicca.capafy-loop-daily"
DOMAIN="gui/$(id -u)"
LIFE_MANAGER_STATE_HOME="${LIFE_MANAGER_STATE_HOME:-$HOME/.local/state/life-manager}"
MARK="$LIFE_MANAGER_STATE_HOME/state/capafy-autopublish/.capafy-healthy-pass"
LOG="$LIFE_MANAGER_STATE_HOME/logs/capafy-loop-healthcheck.log"
STALE_SECONDS=$((30 * 60 * 60))
mkdir -p "$(dirname "$LOG")"

if ! launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; then
  echo "$(date '+%F %T') missing launchd owner: $LABEL" >>"$LOG"
  exit 1
fi

now="$(date +%s)"
mtime="$(stat -f %m "$MARK" 2>/dev/null || echo 0)"
age=$((now - mtime))
if [ "$mtime" -gt 0 ] && [ "$age" -lt "$STALE_SECONDS" ]; then
  exit 0
fi

# A stale/missing terminal receipt means the real launchd loop needs a pass.
# kickstart that owner directly; never spawn a parallel executor or disk gate.
if launchctl kickstart -k "$DOMAIN/$LABEL"; then
  echo "$(date '+%F %T') stale healthy-pass (${age}s); kickstarted $LABEL" >>"$LOG"
  exit 0
fi

echo "$(date '+%F %T') failed to kickstart $LABEL" >>"$LOG"
exit 1
