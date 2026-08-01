#!/usr/bin/env bash
# Capafy healthcheck: launchd presence + recent business outcome/contained incident.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "${CAPAFY_HEALTH_PROBE_ONLY:-0}" = "1" ]; then
  printf 'business_health=%s scheduler_only=false repair_sla_minutes=5\n' "$HERE/capafy_business_health.py"
  exit 0
fi
CHECKER="${CAPAFY_BUSINESS_HEALTH_CMD:-$HERE/capafy_business_health.py}"
FIXER="${CAPAFY_SELF_FIX:-$HERE/../self-fix.sh}"
LOG="${CAPAFY_HEALTH_LOG:-$HOME/.openclaw/logs/capafy-loop-healthcheck.log}"
mkdir -p "$(dirname "$LOG")"
if [[ "$CHECKER" = *.py ]]; then
  BUSINESS_HEALTH_JSON="$(python3 "$CHECKER")"; BUSINESS_HEALTH_RC=$?
else
  BUSINESS_HEALTH_JSON="$(bash "$CHECKER")"; BUSINESS_HEALTH_RC=$?
fi
if [ "$BUSINESS_HEALTH_RC" -ne 0 ]; then
  INCIDENT_ID="$(python3 - "$BUSINESS_HEALTH_JSON" <<'PY'
import json,sys
try: print(json.loads(sys.argv[1]).get("incident_id") or "")
except Exception: print("")
PY
)"
  REASON="$(python3 - "$BUSINESS_HEALTH_JSON" <<'PY'
import json,sys
try: print(json.loads(sys.argv[1]).get("reason") or "business outcome health failed")
except Exception: print("business outcome health returned invalid JSON")
PY
)"
  echo "$(date '+%F %T') unhealthy $BUSINESS_HEALTH_JSON" >> "$LOG"
  CAPAFY_INCIDENT_ID="$INCIDENT_ID" bash "$FIXER" capafy \
    "Capafy business-outcome watchdog: $REASON. Evidence: $BUSINESS_HEALTH_JSON" >> "$LOG" 2>&1 || true
  exit 1
fi
if [ "${CAPAFY_HEALTH_SKIP_SCHEDULER_CHECK:-0}" != "1" ]; then
  if ! launchctl print "gui/$(id -u)/ai.anicca.capafy-loop-daily" >/dev/null 2>&1; then
    echo "$(date '+%F %T') unhealthy scheduler_not_loaded" >> "$LOG"
    CAPAFY_INCIDENT_ID="" bash "$FIXER" capafy \
      "Capafy business-outcome watchdog: daily LaunchAgent is not loaded. Restore ai.anicca.capafy-loop-daily and verify a terminal outcome." >> "$LOG" 2>&1 || true
    exit 1
  fi
fi
echo "$(date '+%F %T') healthy $BUSINESS_HEALTH_JSON" >> "$LOG"
exit 0
