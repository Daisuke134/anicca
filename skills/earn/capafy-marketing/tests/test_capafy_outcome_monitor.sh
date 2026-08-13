#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
OUTCOME="$ROOT/skills/earn/capafy-marketing/scripts/capafy_outcome.py"
MONITOR="$ROOT/skills/earn/capafy-marketing/capafy-outcome-monitor.sh"
PASS=0
FAIL=0

ok() { echo "  ok $1"; PASS=$((PASS + 1)); }
bad() { echo "  FAIL $1: $2"; FAIL=$((FAIL + 1)); }
assert_eq() { [ "$2" = "$3" ] && ok "$1" || bad "$1" "want '$3', got '$2'"; }
assert_has() { printf '%s' "$2" | grep -qiF "$3" && ok "$1" || bad "$1" "missing '$3'"; }
assert_not_has() { printf '%s' "$2" | grep -qiF "$3" && bad "$1" "unexpected '$3'" || ok "$1"; }

setup_case() {
  CASE_DIR="$(mktemp -d)"
  STATE="$CASE_DIR/state"
  mkdir -p "$STATE"
  FAKE_MESSAGES="$CASE_DIR/messages"
  FAKE_COUNT="$CASE_DIR/count"
  FAKE_SENDER="$CASE_DIR/send-telegram.sh"
  printf '0\n' > "$FAKE_COUNT"
  printf '%s\n' \
    '#!/usr/bin/env bash' \
    'n=$(cat "$FAKE_COUNT")' \
    'printf "%s\n" "$((n + 1))" > "$FAKE_COUNT"' \
    'printf "%s\n" "$1" >> "$FAKE_MESSAGES"' \
    'if [ "${FAKE_SEND_RC:-0}" -ne 0 ]; then exit "$FAKE_SEND_RC"; fi' \
    'printf "%s\n" "${FAKE_SEND_OUTPUT:-TELEGRAM_SENT=true MSGID=12345}"' \
    > "$FAKE_SENDER"
  chmod +x "$FAKE_SENDER"
  export CAPAFY_OUTCOME_STATE_DIR="$STATE"
  export CAPAFY_OUTCOME_SCRIPT="$OUTCOME"
  export CAPAFY_TELEGRAM_SENDER="$FAKE_SENDER"
  export FAKE_MESSAGES FAKE_COUNT FAKE_SEND_OUTPUT
  unset FAKE_SEND_OUTPUT FAKE_SEND_RC
}

seed_incident() {
  local phase_payload="${1:-}"
  INCIDENT_JSON="$(python3 "$OUTCOME" start-incident \
    --owner builder \
    --summary 'Builder could not submit because browser ownership collided' \
    --fingerprint browser-owner-collision \
    --repair-result-path "$STATE/.self-fix-capafy-loop.result")"
  INCIDENT_ID="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["incident_id"])' <<<"$INCIDENT_JSON")"
  if [ -n "$phase_payload" ]; then
    printf '%s' "$phase_payload" | python3 "$OUTCOME" transition-incident >/dev/null
  fi
  printf '{"schema_version":1,"incident_id":"%s","loop":"capafy-loop","result_path":"%s"}\n' \
    "$INCIDENT_ID" "$STATE/.self-fix-capafy-loop.result" \
    > "$STATE/.self-fix-capafy-loop.incident.json"
}

incident_record() {
  cat "$STATE/capafy-incidents/$INCIDENT_ID.json"
}

event_count() {
  python3 - "$STATE/capafy-revenue-events.jsonl" "$1" <<'PY'
import json, sys
path, event_id = sys.argv[1:]
with open(path, encoding="utf-8") as stream:
    print(sum(json.loads(line)["event_id"] == event_id for line in stream if line.strip()))
PY
}

echo "(A) RUNNING is silent"
setup_case
seed_incident
printf 'RUNNING 2026-08-01T00:00:00Z\n' > "$STATE/.self-fix-capafy-loop.result"
bash "$MONITOR" >/dev/null 2>&1; rc=$?
assert_eq "RUNNING exits cleanly" "$rc" "0"
assert_eq "RUNNING sends zero messages" "$(cat "$FAKE_COUNT")" "0"
rm -rf "$CASE_DIR"

echo "(B) SUCCESS without verified outcome is reported unresolved"
setup_case
seed_incident
printf 'SUCCESS 2026-08-01T00:10:00Z patched code only\n' > "$STATE/.self-fix-capafy-loop.result"
bash "$MONITOR" >/dev/null 2>&1; rc=$?
body="$(cat "$FAKE_MESSAGES" 2>/dev/null)"
assert_eq "unverified SUCCESS report exits cleanly" "$rc" "0"
assert_eq "unverified SUCCESS sends once" "$(cat "$FAKE_COUNT")" "1"
assert_has "unverified SUCCESS names missing business verification" "$body" "business outcome is not verified"
assert_not_has "unverified SUCCESS never claims closure" "$body" "no action needed"
rm -rf "$CASE_DIR"

echo "(C) verified SUCCESS closes once with real evidence"
setup_case
seed_incident
OUTCOME_JSON="$(python3 - "$INCIDENT_ID" <<'PY'
import json, sys
print(json.dumps({
    "schema_version": 1,
    "kind": "repair_closure",
    "incident_id": sys.argv[1],
    "owner": "builder",
    "title": "Portfolio Tracker — Daily Position Review",
    "agent_id": "9480246345",
    "remote_status": 1,
    "skills_confirmed": True,
    "config_confirmed": True,
    "listing_url": "https://capafy.ai/developer/createAgent?source=temp-link&token=2082974745565622272&page=review",
    "gross_usd": 9.99,
    "pending_usd": 8.0,
    "realized_usd": 0.0,
    "mrr_usd": 0.0,
    "cost_usd": 4.777,
    "contribution_usd": -4.777,
    "detected_summary": "The Builder could not submit because browser ownership collided.",
    "repair_summary": "Separated browser ownership and resumed the same submission.",
    "next_action": "Watch for approval"
}))
PY
)"
printf '%s' "$(python3 - "$INCIDENT_ID" <<'PY'
import json, sys
print(json.dumps({"incident_id": sys.argv[1], "phase": "repair_started"}))
PY
)" | python3 "$OUTCOME" transition-incident >/dev/null
printf '%s' "$(python3 - "$INCIDENT_ID" "$OUTCOME_JSON" <<'PY'
import json, sys
print(json.dumps({"incident_id": sys.argv[1], "phase": "repaired", "outcome": json.loads(sys.argv[2])}))
PY
)" | python3 "$OUTCOME" transition-incident >/dev/null
printf 'SUCCESS 2026-08-01T00:10:00Z remote state verified\n' > "$STATE/.self-fix-capafy-loop.result"
bash "$MONITOR" >/dev/null 2>&1; first_rc=$?
bash "$MONITOR" >/dev/null 2>&1; second_rc=$?
body="$(cat "$FAKE_MESSAGES")"
assert_eq "verified closure first run exits zero" "$first_rc" "0"
assert_eq "verified closure second run exits zero" "$second_rc" "0"
assert_eq "verified closure sends exactly once" "$(cat "$FAKE_COUNT")" "1"
assert_has "closure contains real review URL" "$body" "https://capafy.ai/developer/createAgent?source=temp-link&token=2082974745565622272&page=review"
assert_has "closure says no action needed" "$body" "no action needed"
record="$(incident_record)"
assert_has "incident reaches verified" "$record" '"phase": "verified"'
assert_eq "real Telegram message id is numeric" "$(python3 -c 'import json,sys;print(str(isinstance(json.load(sys.stdin).get("telegram_message_id"),int)).lower())' <<<"$record")" true
assert_has "verified state carries concrete verification" "$record" '"business_outcome_validated": true'
assert_has "verified closure confirms Telegram delivery" "$record" '"telegram_delivery_status": "confirmed"'
assert_eq "verified state carries numeric Telegram id" "$(python3 -c 'import json,sys;print(str(isinstance(json.load(sys.stdin)["verification"].get("telegram_message_id"),int)).lower())' <<<"$record")" true
assert_eq "detected event exists exactly once" "$(event_count "capafy:incident.detected:$INCIDENT_ID")" "1"
assert_eq "repair-started event exists exactly once" "$(event_count "capafy:incident.repair_started:$INCIDENT_ID")" "1"
assert_eq "repaired event exists exactly once" "$(event_count "capafy:incident.repaired:$INCIDENT_ID")" "1"
assert_eq "verified event exists exactly once" "$(event_count "capafy:incident.verified:$INCIDENT_ID")" "1"
rm -rf "$CASE_DIR"

echo "(C2) failed closure reserves, verifies business outcome, and never retries Telegram"
setup_case
seed_incident
printf '%s' "$(python3 - "$INCIDENT_ID" <<'PY'
import json,sys
print(json.dumps({"incident_id":sys.argv[1],"phase":"detected","outcome":{
    "schema_version": 1,
    "kind": "repair_closure",
    "owner": "builder",
    "title": "Portfolio Tracker — Daily Position Review",
    "listing_url": "https://capafy.ai/developer/createAgent?source=temp-link&token=2082974745565622272&page=review",
    "agent_id": "9480246345",
    "remote_status": 1,
    "skills_confirmed": True,
    "config_confirmed": True,
    "gross_usd": 9.99,
    "pending_usd": 8.0,
    "realized_usd": 0.0,
    "mrr_usd": 0.0,
    "cost_usd": 4.777,
    "contribution_usd": -4.777,
    "detected_summary": "The Builder could not submit because browser ownership collided.",
    "repair_summary": "Separated browser ownership and resumed the same submission.",
    "next_action": "Watch for approval",
}}))
PY
)" | python3 "$OUTCOME" transition-incident >/dev/null
printf 'SUCCESS 2026-08-01T00:10:00Z remote state verified\n' > "$STATE/.self-fix-capafy-loop.result"
FAKE_SEND_RC=9
export FAKE_SEND_RC
bash "$MONITOR" >/dev/null 2>&1; first_rc=$?
record="$(incident_record)"
[ "$first_rc" -ne 0 ] && ok "failed closure returns nonzero" || bad "failed closure returns nonzero" "rc=$first_rc"
assert_has "failed closure reaches verified" "$record" '"phase": "verified"'
assert_has "failed closure retains reservation" "$record" '"terminal_message_key":'
assert_has "failed closure records business verification" "$record" '"business_outcome_validated": true'
assert_has "failed closure records unconfirmed Telegram status" "$record" '"telegram_delivery_status": "reserved_unconfirmed"'
assert_not_has "failed closure fabricates no Telegram id" "$record" '"telegram_message_id":'
assert_eq "failed closure verified event exists exactly once" "$(event_count "capafy:incident.verified:$INCIDENT_ID")" "1"
assert_eq "failed closure sender is attempted once" "$(cat "$FAKE_COUNT")" "1"
FAKE_SEND_RC=0
FAKE_SEND_OUTPUT='TELEGRAM_SENT=true MSGID=54321'
export FAKE_SEND_RC FAKE_SEND_OUTPUT
bash "$MONITOR" >/dev/null 2>&1; replay_rc=$?
assert_eq "failed closure replay exits cleanly" "$replay_rc" "0"
assert_eq "failed closure replay never retries Telegram" "$(cat "$FAKE_COUNT")" "1"
rm -rf "$CASE_DIR"

echo "(D) FAIL reports blocker and next retry"
setup_case
seed_incident
retry='2026-08-01T18:00:00+09:00'
canonical_retry='2026-08-01T09:00:00Z'
printf '%s' "$(python3 - "$INCIDENT_ID" "$retry" <<'PY'
import json, sys
print(json.dumps({"incident_id": sys.argv[1], "phase": "unresolved", "repair_summary": "One clean reattach still returned ChallengeRequired", "next_retry_at": sys.argv[2]}))
PY
)" | python3 "$OUTCOME" transition-incident >/dev/null
printf 'FAIL 2026-08-01T00:10:00Z Instagram challenge remains\n' > "$STATE/.self-fix-capafy-loop.result"
bash "$MONITOR" >/dev/null 2>&1; rc=$?
body="$(cat "$FAKE_MESSAGES")"
assert_eq "FAIL report exits zero" "$rc" "0"
assert_has "FAIL contains attempted repair" "$body" "One clean reattach"
assert_has "FAIL contains remaining blocker" "$body" "Instagram challenge remains"
assert_has "FAIL contains canonical next retry" "$body" "$canonical_retry"
rm -rf "$CASE_DIR"

echo "(E) first-send failure reserves once and replay never retries Telegram"
setup_case
seed_incident
printf 'SUCCESS 2026-08-01T00:10:00Z patched code only\n' > "$STATE/.self-fix-capafy-loop.result"
FAKE_SEND_OUTPUT='TELEGRAM_SENT=false'
export FAKE_SEND_OUTPUT
bash "$MONITOR" >/dev/null 2>&1; rc=$?
record="$(incident_record)"
[ "$rc" -ne 0 ] && ok "sender without message id returns nonzero" || bad "sender without message id returns nonzero" "rc=$rc"
assert_not_has "failed sender reserves delivery key" "$record" '"terminal_message_key": null'
assert_not_has "failed sender leaves Telegram id unset" "$record" '"telegram_message_id":'
assert_eq "failed sender is attempted once" "$(cat "$FAKE_COUNT")" "1"
FAKE_SEND_OUTPUT='TELEGRAM_SENT=true MSGID=54321'
export FAKE_SEND_OUTPUT
bash "$MONITOR" >/dev/null 2>&1; rc=$?
assert_eq "reserved sender replay exits cleanly" "$rc" "0"
assert_eq "reserved sender replay never retries Telegram" "$(cat "$FAKE_COUNT")" "1"
rm -rf "$CASE_DIR"

echo "(F) changed retry text cannot resend an unresolved reservation"
setup_case
seed_incident
printf 'FAIL 2026-08-01T00:10:00Z first blocker\n' > "$STATE/.self-fix-capafy-loop.result"
bash "$MONITOR" >/dev/null 2>&1; first_rc=$?
first_record="$(incident_record)"
first_key="$(python3 -c 'import json,sys;print(json.load(sys.stdin)["terminal_message_key"])' <<<"$first_record")"
assert_eq "initial unresolved report exits cleanly" "$first_rc" "0"
assert_eq "initial unresolved report sends once" "$(cat "$FAKE_COUNT")" "1"
printf '%s' "$(python3 - "$INCIDENT_ID" <<'PY'
import json,sys
print(json.dumps({"incident_id":sys.argv[1],"phase":"unresolved","repair_summary":"Changed repair text","next_retry_at":"2099-01-01T00:09:00Z"}))
PY
)" | python3 "$OUTCOME" transition-incident >/dev/null
printf 'FAIL 2026-08-01T00:11:00Z changed blocker\n' > "$STATE/.self-fix-capafy-loop.result"
bash "$MONITOR" >/dev/null 2>&1; changed_rc=$?
changed_record="$(incident_record)"
assert_eq "changed retry replay exits cleanly" "$changed_rc" "0"
assert_eq "changed retry sends zero additional messages" "$(cat "$FAKE_COUNT")" "1"
assert_eq "changed retry preserves original reservation" "$(python3 -c 'import json,sys;print(json.load(sys.stdin)["terminal_message_key"])' <<<"$changed_record")" "$first_key"
rm -rf "$CASE_DIR"

echo "(G) spoofed and multiline sender output are rejected"
for malformed in spoof multiline; do
  setup_case
  seed_incident
  printf 'SUCCESS 2026-08-01T00:10:00Z patched code only\n' > "$STATE/.self-fix-capafy-loop.result"
  if [ "$malformed" = spoof ]; then
    FAKE_SEND_OUTPUT='noise TELEGRAM_SENT=true MSGID=7001'
  else
    FAKE_SEND_OUTPUT=$'TELEGRAM_SENT=true MSGID=7001\nextra'
  fi
  export FAKE_SEND_OUTPUT
  bash "$MONITOR" >/dev/null 2>&1; malformed_rc=$?
  malformed_record="$(incident_record)"
  [ "$malformed_rc" -ne 0 ] && ok "$malformed sender output fails" || bad "$malformed sender output fails" "rc=$malformed_rc"
  assert_not_has "$malformed sender reserves before rejection" "$malformed_record" '"terminal_message_key": null'
  assert_not_has "$malformed sender stores no id" "$malformed_record" '"telegram_message_id":'
  rm -rf "$CASE_DIR"
done

echo "(H) stale code-only sidecar cannot reopen a verified incident"
setup_case
seed_incident
for phase in repair_started repaired verified; do
  printf '%s' "$(python3 - "$INCIDENT_ID" "$phase" <<'PY'
import json, sys
payload = {"incident_id": sys.argv[1], "phase": sys.argv[2]}
if sys.argv[2] == "verified":
    payload.update({
        "terminal_message_key": "marketing-published-verified-reel",
        "telegram_message_id": "5166",
        "verification": {
            "owner_session_verified": True,
            "reel_url": "https://www.instagram.com/reel/DbgsvEbo5kd/",
        },
    })
print(json.dumps(payload))
PY
)" | python3 "$OUTCOME" transition-incident >/dev/null
done
before="$(incident_record)"
printf 'SUCCESS 2026-08-01T19:23:04Z code work complete without attached outcome\n' > "$STATE/.self-fix-capafy-loop.result"
bash "$MONITOR" >/dev/null 2>&1; rc=$?
after="$(incident_record)"
assert_eq "verified stale sidecar exits cleanly" "$rc" "0"
assert_eq "verified stale sidecar sends zero messages" "$(cat "$FAKE_COUNT")" "0"
assert_eq "verified stale sidecar preserves terminal incident" "$after" "$before"
rm -rf "$CASE_DIR"

echo "=== capafy outcome monitor: $PASS passed $FAIL failed ==="
[ "$FAIL" -eq 0 ] || exit 1
