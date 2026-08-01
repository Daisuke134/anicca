#!/usr/bin/env bash
# Deterministic terminal classifier for the Capafy Builder pass.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
set -uo pipefail

RUNNER_RC="${1:-1}"
EVIDENCE_DIR="${2:-none}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE="${CAPAFY_OUTCOME_STATE_DIR:-$HOME/.openclaw/state}"
RESULT="${CAPAFY_BUILDER_RESULT:-$STATE/capafy-builder-result.json}"
OUTCOME="${CAPAFY_OUTCOME_SCRIPT:-$HERE/../../earn/capafy-marketing/scripts/capafy_outcome.py}"
SENDER="${CAPAFY_TELEGRAM_SENDER:-$HERE/../../_shared/send-telegram.sh}"
FIXER="${CAPAFY_SELF_FIX:-$HERE/../self-fix.sh}"
TERMINAL="$STATE/capafy-builder-terminal.json"
mkdir -p "$STATE"

read_result_field(){
  python3 - "$RESULT" "$1" <<'PY'
import json, sys
try:
    value = json.load(open(sys.argv[1])).get(sys.argv[2])
except Exception:
    value = None
print("" if value is None else value)
PY
}

send_with_receipt(){
  local body="$1" response message_id
  response="$(bash "$SENDER" "$body" 2>&1)" || return 1
  message_id="$(printf '%s\n' "$response" | sed -nE 's/.*MSGID=([0-9]+).*/\1/p' | tail -1)"
  [ -n "$message_id" ] || return 1
  printf '%s' "$message_id"
}

start_failure(){
  local reason="$1" fingerprint incident phase body
  fingerprint="$(printf '%s' "$reason" | shasum -a 256 | awk '{print $1}')"
  incident="$(python3 "$OUTCOME" start-incident --owner builder --summary "$reason" --fingerprint "$fingerprint" --repair-result-path "$STATE/.self-fix-capafy-loop.result")" || return 2
  INCIDENT_ID="$(python3 - "$incident" <<'PY'
import json, sys
print(json.loads(sys.argv[1])["incident_id"])
PY
)"
  phase="$(python3 - "$incident" <<'PY'
import json, sys
print(json.loads(sys.argv[1])["phase"])
PY
)"
  if [ "$phase" = "detected" ]; then
    printf '%s' "$(python3 - "$INCIDENT_ID" <<'PY'
import json, sys
print(json.dumps({"incident_id": sys.argv[1], "phase": "repair_started"}))
PY
)" | python3 "$OUTCOME" transition-incident >/dev/null || return 2
    body="Capafy Builder hit a verified terminal blocker. Incident $INCIDENT_ID is now in automatic repair. Reason: $reason. Evidence directory: $EVIDENCE_DIR. No human action is required."
    send_with_receipt "$body" >/dev/null || true
    CAPAFY_INCIDENT_ID="$INCIDENT_ID" FIX_CALLS="${FIX_CALLS:-}" bash "$FIXER" capafy "$reason" || return 2
  fi
  return 1
}

if [ "$RUNNER_RC" -ne 0 ]; then
  reason="$(read_result_field reason)"
  [ -n "$reason" ] || reason="Builder runner exited rc=$RUNNER_RC without a verified terminal outcome"
  start_failure "$reason"; exit $?
fi

[ -f "$RESULT" ] || { start_failure "Builder runner exited zero but produced no deterministic result artifact"; exit $?; }
RESULT_KIND="$(read_result_field result)"

if [ "$RESULT_KIND" = "failure" ]; then
  reason="$(read_result_field reason)"; [ -n "$reason" ] || reason="Builder reported an unspecified failure"
  start_failure "$reason"; exit $?
fi

money_json(){
  if [ -n "${CAPAFY_MONEY_JSON:-}" ] && [ -f "$CAPAFY_MONEY_JSON" ]; then
    cat "$CAPAFY_MONEY_JSON"
    return
  fi
  python3 - "$HOME/anicca/skills/self/capafy-loop/state/STATE.md" "$HOME/.openclaw/logs/capafy-loop-daily.log" <<'PY'
import json, re, sys
values = {}
try:
    for line in open(sys.argv[1], errors="ignore"):
        match = re.match(r"(capafy_[a-z_]+):\s*([-0-9.]+)", line)
        if match:
            values[match.group(1)] = float(match.group(2))
except OSError:
    pass
cost = 0.0
try:
    for line in open(sys.argv[2], errors="ignore"):
        try: row = json.loads(line)
        except Exception: continue
        if row.get("provider") == "openrouter" and row.get("total_usage_usd") is not None:
            cost = float(row["total_usage_usd"])
except OSError:
    pass
realized = values.get("capafy_realized_payout_usd", 0.0)
print(json.dumps({
    "gross_usd": values.get("capafy_lifetime_gross_usd", 0.0),
    "pending_usd": values.get("capafy_seller_balance_pending_usd", 0.0),
    "realized_usd": realized,
    "mrr_usd": values.get("capafy_mrr_usd", 0.0),
    "cost_usd": cost,
    "contribution_usd": realized - cost,
}))
PY
}

MONEY="$(money_json)" || { start_failure "Builder money reconciliation could not be read"; exit $?; }

if [ "$RESULT_KIND" = "no-op" ]; then
  reason="$(read_result_field reason)"; [ -n "$reason" ] || reason="bounded pass had no safe submission"
  ENVELOPE="$(python3 - "$MONEY" "$reason" <<'PY'
import json, sys
data = json.loads(sys.argv[1]); data.update({"schema_version": 1, "kind": "builder_noop", "owner": "builder", "reason": sys.argv[2]}); print(json.dumps(data))
PY
)"
else
  [ "$RESULT_KIND" = "submitted" ] || { start_failure "Builder result artifact has unsupported result=$RESULT_KIND"; exit $?; }
  AGENT_ID="$(read_result_field agent_id)"; LISTING_URL="$(read_result_field listing_url)"
  [ -n "$AGENT_ID" ] || { start_failure "Builder submitted result omitted agent_id"; exit $?; }
  if [ -n "${CAPAFY_REMOTE_STATUS_JSON:-}" ] && [ -f "$CAPAFY_REMOTE_STATUS_JSON" ]; then
    REMOTE="$(cat "$CAPAFY_REMOTE_STATUS_JSON")"
  else
    REMOTE="$(cd "$HOME/.openclaw/skills/capafy-autopublish/vendor/capafy-publisher" && python3 packager.py publish-remote-status --agent-id "$AGENT_ID")" || { start_failure "Capafy remote-status read failed for agent_id=$AGENT_ID"; exit $?; }
  fi
  VERIFIED="$(python3 - "$REMOTE" "$AGENT_ID" <<'PY'
import json, sys
try: v=json.loads(sys.argv[1])["latest_version"]
except Exception: print("no"); raise SystemExit
same=str(v.get("agentId") or v.get("agent_id") or sys.argv[2]) == sys.argv[2]
print("yes" if same and v.get("status") in (1,4) and v.get("isConfirmedSkills")==1 and v.get("isConfirmedConfigKeys")==1 else "no")
PY
)"
  [ "$VERIFIED" = "yes" ] || { start_failure "Capafy remote readback is not submitted: agent_id=$AGENT_ID"; exit $?; }
  ENVELOPE="$(python3 - "$REMOTE" "$MONEY" "$AGENT_ID" "$LISTING_URL" <<'PY'
import json, sys
v=json.loads(sys.argv[1])["latest_version"]; data=json.loads(sys.argv[2])
data.update({"schema_version":1,"kind":"builder_submitted","owner":"builder","title":v.get("title") or "Untitled Capafy skill","agent_id":sys.argv[3],"remote_status":v["status"],"skills_confirmed":v["isConfirmedSkills"]==1,"config_confirmed":v["isConfirmedConfigKeys"]==1,"listing_url":sys.argv[4],"next_action":"Watch for approval and hand the public listing to Marketing"})
print(json.dumps(data))
PY
)"
fi

BODY="$(printf '%s' "$ENVELOPE" | python3 "$OUTCOME" render)" || { start_failure "Builder terminal outcome failed validation"; exit $?; }
KEY="$(printf '%s' "$ENVELOPE" | python3 "$OUTCOME" delivery-key)" || exit 2
if [ -f "$TERMINAL" ] && python3 - "$TERMINAL" "$KEY" <<'PY'
import json, sys
try: same=json.load(open(sys.argv[1])).get("delivery_key")==sys.argv[2]
except Exception: same=False
raise SystemExit(0 if same else 1)
PY
then exit 0; fi
MESSAGE_ID="$(send_with_receipt "$BODY")" || exit 2
python3 - "$TERMINAL" "$KEY" "$MESSAGE_ID" "$ENVELOPE" <<'PY'
import datetime, json, os, sys
path,key,msg,envelope=sys.argv[1:5]; tmp=path+".tmp"
payload={"schema_version":1,"delivery_key":key,"telegram_message_id":msg,"recorded_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"outcome":json.loads(envelope)}
with open(tmp,"w") as f: json.dump(payload,f,ensure_ascii=False,indent=2); f.write("\n"); f.flush(); os.fsync(f.fileno())
os.replace(tmp,path)
PY
exit 0
