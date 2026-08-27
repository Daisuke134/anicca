#!/usr/bin/env bash
# Supervise the single launchd-owned Capafy daily pass. Do not create a second
# tmux/Claude scheduler: ai.anicca.capafy-loop-daily is the only execution owner.
set -uo pipefail

LABEL="ai.anicca.capafy-loop-daily"
DOMAIN="gui/$(id -u)"
LIFE_MANAGER_STATE_HOME="${LIFE_MANAGER_STATE_HOME:-$HOME/.local/state/life-manager}"
MARK="$LIFE_MANAGER_STATE_HOME/state/capafy-autopublish/.capafy-healthy-pass"
LOG="$LIFE_MANAGER_STATE_HOME/logs/capafy-loop-healthcheck.log"
EVIDENCE_ROOT="$LIFE_MANAGER_STATE_HOME/state/agent-runner-evidence/capafy-marketplace"
BACKOFF="$LIFE_MANAGER_STATE_HOME/state/capafy-provider-backoff.json"
STALE_SECONDS=$((30 * 60 * 60))
ATTEMPT_GRACE_SECONDS=$((2 * 60 * 60))
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

# A recent attempt proves launchd is scheduling the owner. Let the hourly
# cadence retry it; the five-minute monitor must not overlap or amplify it.
LATEST_ATTEMPT="$(find "$EVIDENCE_ROOT" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort | tail -1)"
LATEST_START="$(basename "$LATEST_ATTEMPT" 2>/dev/null | cut -d- -f1)"
case "$LATEST_START" in
  ''|*[!0-9]*) ;;
  *)
    if [ $((now - LATEST_START)) -lt "$ATTEMPT_GRACE_SECONDS" ]; then
      exit 0
    fi
    ;;
esac

# Provider quota is not a dead scheduler. The hourly owner will try again on
# its normal cadence; a five-minute kickstart here only amplifies the outage.
LATEST_SUMMARY="$(find "$EVIDENCE_ROOT" -mindepth 2 -maxdepth 2 -type f -name summary.json 2>/dev/null | sort | tail -1)"
LATEST="${LATEST_SUMMARY%/summary.json}"
if [ -n "$LATEST" ] && python3 - "$LATEST/summary.json" "$LATEST/attempts.jsonl" <<'PY'
import json
import sys

try:
    summary = json.load(open(sys.argv[1], encoding="utf-8"))
    attempts = [json.loads(line) for line in open(sys.argv[2], encoding="utf-8") if line.strip()]
except (OSError, ValueError, TypeError):
    raise SystemExit(1)
raise SystemExit(0 if summary.get("status") == "failed" and attempts
                 and all(row.get("error_class") == "transient_quota" for row in attempts) else 1)
PY
then
  next_eligible=$((now + 60 * 60))
  mkdir -p "$(dirname "$BACKOFF")"
  python3 - "$BACKOFF" "$now" "$next_eligible" <<'PY'
import json
import os
import sys
import tempfile

target, observed, eligible = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
fd, temporary = tempfile.mkstemp(prefix=".capafy-provider-backoff.", dir=os.path.dirname(target))
try:
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump({"error_class": "transient_quota", "observed_at_epoch": observed,
                   "next_eligible_at_epoch": eligible}, handle, separators=(",", ":"))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, target)
finally:
    if os.path.exists(temporary):
        os.unlink(temporary)
PY
  echo "$(date '+%F %T') provider quota; hourly owner backoff until epoch $next_eligible; no kickstart" >>"$LOG"
  exit 0
fi

echo "$(date '+%F %T') stale healthy-pass (${age}s); lifecycle repair required via lm-loop for $LABEL" >>"$LOG"
exit 1
