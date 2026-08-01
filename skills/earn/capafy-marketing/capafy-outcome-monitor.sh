#!/usr/bin/env bash
# Deliver a Capafy self-fix terminal outcome once, only after deterministic validation.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE="${CAPAFY_OUTCOME_STATE_DIR:-$HOME/.openclaw/state}"
OUTCOME="${CAPAFY_OUTCOME_SCRIPT:-$SCRIPT_DIR/scripts/capafy_outcome.py}"
SENDER="${CAPAFY_TELEGRAM_SENDER:-$SCRIPT_DIR/../../_shared/send-telegram.sh}"
SIDECAR="$STATE/.self-fix-capafy-loop.incident.json"
LOCK="$STATE/.capafy-outcome-monitor.lock"
mkdir -p "$STATE"

if ! mkdir "$LOCK" 2>/dev/null; then
  lock_mtime="$(stat -f %m "$LOCK" 2>/dev/null || echo 0)"
  if [ $(( $(date +%s) - lock_mtime )) -gt 600 ]; then
    rm -rf "$LOCK"
    mkdir "$LOCK" 2>/dev/null || exit 0
  else
    exit 0
  fi
fi
trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT

[ -f "$SIDECAR" ] || exit 0
INCIDENT_ID="$(python3 - "$SIDECAR" <<'PY'
import json, sys
try:
    print(json.load(open(sys.argv[1]))["incident_id"])
except Exception:
    raise SystemExit(2)
PY
)" || exit 2
RESULT_PATH="$(python3 - "$SIDECAR" <<'PY'
import json, sys
try:
    print(json.load(open(sys.argv[1]))["result_path"])
except Exception:
    raise SystemExit(2)
PY
)" || exit 2
[ -f "$RESULT_PATH" ] || exit 0

RESULT_LINE="$(head -1 "$RESULT_PATH" 2>/dev/null)"
RESULT_STATUS="${RESULT_LINE%% *}"
case "$RESULT_STATUS" in
  RUNNING|'') exit 0 ;;
  SUCCESS|FAIL) ;;
  *) exit 0 ;;
esac

RECORD="$(python3 "$OUTCOME" get-incident --incident-id "$INCIDENT_ID")" || exit 2
ENVELOPE="$(python3 - "$RECORD" "$RESULT_STATUS" "$RESULT_LINE" <<'PY'
import json, sys
record = json.loads(sys.argv[1])
status, result_line = sys.argv[2:4]
outcome = record.get("outcome")
if status == "SUCCESS" and isinstance(outcome, dict):
    print(json.dumps(outcome, ensure_ascii=False))
    raise SystemExit(0)
detail = result_line.split(" ", 2)[2] if len(result_line.split(" ", 2)) == 3 else result_line
if status == "SUCCESS":
    repair = "The self-fixer completed its code work, but the original business observable was not attached."
    blocker = "The business outcome is not verified; code completion alone cannot close this incident."
else:
    repair = record.get("repair_summary") or "The autonomous repair ran and returned a terminal failure."
    blocker = detail or record.get("summary") or "The blocker remains unresolved."
print(json.dumps({
    "schema_version": 1,
    "kind": "incident_unresolved",
    "incident_id": record["incident_id"],
    "owner": record["owner"],
    "detected_summary": record.get("summary") or "A Capafy operation failed.",
    "repair_summary": repair,
    "blocker": blocker,
    "next_retry_at": record.get("next_retry_at") or "the next scheduled repair cycle",
}, ensure_ascii=False))
PY
)" || exit 2

BODY="$(printf '%s' "$ENVELOPE" | python3 "$OUTCOME" render)" || exit 2
KEY="$(printf '%s' "$ENVELOPE" | python3 "$OUTCOME" delivery-key)" || exit 2
CURRENT_KEY="$(python3 - "$RECORD" <<'PY'
import json, sys
print(json.loads(sys.argv[1]).get("terminal_message_key") or "")
PY
)"
[ "$CURRENT_KEY" = "$KEY" ] && exit 0

SEND_RESULT="$(bash "$SENDER" "$BODY" 2>&1)" || exit 1
MESSAGE_ID="$(printf '%s\n' "$SEND_RESULT" | sed -nE 's/.*MSGID=([0-9]+).*/\1/p' | tail -1)"
[ -n "$MESSAGE_ID" ] || exit 1

KIND="$(python3 - "$ENVELOPE" <<'PY'
import json, sys
print(json.loads(sys.argv[1])["kind"])
PY
)"
CURRENT_PHASE="$(python3 - "$RECORD" <<'PY'
import json, sys
print(json.loads(sys.argv[1])["phase"])
PY
)"

transition() {
  local phase="$1" extra="${2:-}"
  [ -n "$extra" ] || extra='{}'
  python3 - "$INCIDENT_ID" "$phase" "$extra" <<'PY' | python3 "$OUTCOME" transition-incident >/dev/null
import json, sys
payload = json.loads(sys.argv[3])
payload.update({"incident_id": sys.argv[1], "phase": sys.argv[2]})
print(json.dumps(payload))
PY
}

if [ "$KIND" = "repair_closure" ]; then
  case "$CURRENT_PHASE" in
    detected) transition repair_started || exit 2; transition repaired || exit 2 ;;
    repair_started) transition repaired || exit 2 ;;
    unresolved) transition repair_started || exit 2; transition repaired || exit 2 ;;
    repaired) ;;
    verified) exit 0 ;;
  esac
  transition verified "$(printf '{"terminal_message_key":"%s","telegram_message_id":"%s"}' "$KEY" "$MESSAGE_ID")" || exit 2
else
  transition unresolved "$(printf '{"terminal_message_key":"%s","telegram_message_id":"%s"}' "$KEY" "$MESSAGE_ID")" || exit 2
fi

exit 0
