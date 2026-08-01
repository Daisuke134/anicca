#!/usr/bin/env bash
# Deterministic terminal classifier for the Capafy Instagram marketing pass.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
set -uo pipefail
RUNNER_RC="${1:-1}"; EVIDENCE_DIR="${2:-none}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE="${CAPAFY_OUTCOME_STATE_DIR:-$HOME/.openclaw/state}"
RESULT="${CAPAFY_MARKETING_RESULT:-$STATE/capafy-marketing-result.json}"
OUTCOME="${CAPAFY_OUTCOME_SCRIPT:-$HERE/scripts/capafy_outcome.py}"
SENDER="${CAPAFY_TELEGRAM_SENDER:-$HERE/../../_shared/send-telegram.sh}"
TERMINAL="$STATE/capafy-marketing-terminal.json"
mkdir -p "$STATE"

field(){ python3 - "$RESULT" "$1" <<'PY'
import json,sys
try: value=json.load(open(sys.argv[1])).get(sys.argv[2])
except Exception: value=None
print("" if value is None else value)
PY
}
send_receipt(){
  local response id
  response="$(bash "$SENDER" "$1" 2>&1)" || return 1
  id="$(printf '%s\n' "$response"|sed -nE 's/.*MSGID=([0-9]+).*/\1/p'|tail -1)"
  [ -n "$id" ] || return 1; printf '%s' "$id"
}
record_terminal(){
  python3 - "$TERMINAL" "$1" "$2" <<'PY'
import datetime,json,os,sys
path,msg,envelope=sys.argv[1:4]; tmp=path+".tmp"
data={"schema_version":1,"telegram_message_id":msg,"recorded_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"outcome":json.loads(envelope)}
with open(tmp,"w") as f: json.dump(data,f,ensure_ascii=False,indent=2); f.write("\n"); f.flush(); os.fsync(f.fileno())
os.replace(tmp,path)
PY
}
incident(){
  local reason="$1" lifecycle="$2" retry="$3" fingerprint raw id payload body msg
  fingerprint="$(printf '%s' "$reason"|shasum -a 256|awk '{print $1}')"
  raw="$(python3 "$OUTCOME" start-incident --owner marketer --summary "$reason" --fingerprint "$fingerprint")" || return 2
  id="$(python3 -c 'import json,sys;print(json.load(sys.stdin)["incident_id"])' <<<"$raw")"
  payload="$(python3 - "$id" "$reason" "$lifecycle" "$retry" <<'PY'
import json,sys
print(json.dumps({"incident_id":sys.argv[1],"phase":"unresolved","repair_summary":sys.argv[3],"next_retry_at":sys.argv[4]}))
PY
)"
  printf '%s' "$payload"|python3 "$OUTCOME" transition-incident >/dev/null || true
  body="Capafy Marketer incident $id: $reason. $lifecycle. Next automatic action: $retry. Evidence: $EVIDENCE_DIR. Human action required: none."
  msg="$(send_receipt "$body")" || return 2
  return 1
}

[ -f "$RESULT" ] || { incident "marketing runner produced no deterministic terminal artifact (rc=$RUNNER_RC)" "The technical repair owner will inspect the runner boundary" "the next repair cycle"; exit $?; }
KIND="$(field result)"
if [ "$KIND" = "challenge" ]; then
  reason="$(field reason)"; retry="$(field next_retry_at)"; [ -n "$retry" ]||retry="the next account lifecycle pass"
  incident "Instagram platform challenge on @$(field handle): $reason" "Retries are contained and the replacement-account workflow is active" "$retry"; exit $?
fi
if [ "$RUNNER_RC" -ne 0 ] || [ "$KIND" = "failure" ]; then
  reason="$(field reason)"; [ -n "$reason" ]||reason="marketing runner exited rc=$RUNNER_RC"
  incident "$reason" "The technical repair owner is active; this is not evidence of an account ban" "the next repair cycle"; exit $?
fi

case "$KIND" in
  scheduled)
    ENVELOPE="$(python3 - "$(field handle)" <<'PY'
import json,sys
print(json.dumps({"schema_version":1,"kind":"account_state","owner":"marketer","handle":sys.argv[1] or "unknown","scheduler_loaded":True,"calendar_warmup_day":0,"session_established":False,"public_post_url":None}))
PY
)" ;;
  dry)
    ENVELOPE="$(cat "$RESULT"|python3 -c 'import json,sys;d=json.load(sys.stdin);d["schema_version"]=1;d["kind"]="marketing_dry";d["owner"]="marketer";d.pop("result",None);print(json.dumps(d))')" ;;
  published)
    ENVELOPE="$(cat "$RESULT"|python3 -c 'import json,sys;d=json.load(sys.stdin);d["schema_version"]=1;d["kind"]="marketing_published";d["owner"]="marketer";d.pop("result",None);print(json.dumps(d))')" ;;
  *) incident "unsupported marketing terminal result=$KIND" "The technical repair owner will repair the outcome contract" "the next repair cycle"; exit $? ;;
esac

MEDIA_PATH="$(python3 - "$ENVELOPE" <<'PY'
import json,sys
print(json.loads(sys.argv[1]).get("media_path") or "")
PY
)"
if [ -n "$MEDIA_PATH" ] && [ ! -f "$MEDIA_PATH" ]; then
  incident "marketing media artifact is missing: $MEDIA_PATH" "The content pass cannot claim completion without its real media" "the next repair cycle"; exit $?
fi
BODY="$(printf '%s' "$ENVELOPE"|python3 "$OUTCOME" render)" || { incident "marketing terminal outcome failed validation" "Missing evidence prevents a publish claim" "the next repair cycle"; exit $?; }
MSG_ID="$(send_receipt "$BODY")" || exit 2
record_terminal "$MSG_ID" "$ENVELOPE"
exit 0
