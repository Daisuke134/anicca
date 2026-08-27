#!/usr/bin/env bash
# Healthcheck for the bounded bounty pass. Lifecycle repair belongs to lm-loop; this reports only.
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"

RUN_AGENT="$HOME/anicca/skills/earn/marketing-engine/run_agent.sh"
if [ "${AGENT_WIRING_PROBE_ONLY:-0}" = "1" ]; then
  printf '{"task_class":"high-value-agent","runner":"%s"}\n' "$RUN_AGENT"
  exit 0
fi

PASS_LOCK="/tmp/anicca-bounty-pass.lock"
CLI="$HOME/profitable-claude/skills/bounty/bounty-cli.sh"
DAILY_LABEL="ai.anicca.hf-bounty-daily"
HB="$HOME/.openclaw/state/.bounty-core-last-pass"
START="$HOME/.openclaw/state/.bounty-core-last-start"
LOG="$HOME/.openclaw/logs/bounty-core-healthcheck.log"
STALE_MIN=1560
LOCK_DIR="/tmp/.bounty-healthcheck.lock"
mkdir -p "$(dirname "$LOG")" "$HOME/.openclaw/state"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then exit 0; fi
trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT

if [ -d "$PASS_LOCK" ]; then
  age=$(( $(date +%s) - $(stat -f %m "$PASS_LOCK" 2>/dev/null || echo 0) ))
  if [ "$age" -lt 2700 ]; then
    echo "$(date '+%F %T') bounded bounty pass RUNNING (${age}s)" >> "$LOG"
    exit 0
  fi
fi

age_min=999999
if [ -f "$HB" ]; then
  age_min=$(( ($(date +%s) - $(stat -f %m "$HB")) / 60 ))
elif [ -f "$START" ]; then
  start_age=$(( ($(date +%s) - $(stat -f %m "$START")) / 60 ))
  if [ "$start_age" -lt 45 ]; then
    echo "$(date '+%F %T') first bounded bounty pass pending (${start_age}min)" >> "$LOG"
    exit 0
  fi
fi

if [ "$age_min" -lt "$STALE_MIN" ]; then
  echo "$(date '+%F %T') bounty daily heartbeat fresh (${age_min}min)" >> "$LOG"
  exit 0
fi

# The explicit safe seam lets tests exercise the bounded pass without production effects.
if [ "${BOUNTY_HEALTHCHECK_SAFE_PROBE_ONLY:-0}" = "1" ]; then
  probe_root="${BOUNTY_SAFE_PROBE_ROOT:-/private/tmp/bounty-healthcheck-safe-$(date +%s)-$$}"
  BOUNTY_SAFE_PROBE_ONLY=1 BOUNTY_SAFE_PROBE_ROOT="$probe_root" bash "$CLI" >> "$LOG" 2>&1
  echo "$(date '+%F %T') bounty stale recovery safe-probed evidence=$probe_root/evidence" >> "$LOG"
  exit 0
fi
echo "$(date '+%F %T') bounty daily heartbeat stale/missing; lifecycle repair required via lm-loop for $DAILY_LABEL" >> "$LOG"
exit 1
