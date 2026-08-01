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
    'printf "%s\n" "${FAKE_SEND_OUTPUT:-TELEGRAM_SENT=true MSGID=12345}"' \
    > "$FAKE_SENDER"
  chmod +x "$FAKE_SENDER"
  export CAPAFY_OUTCOME_STATE_DIR="$STATE"
  export CAPAFY_OUTCOME_SCRIPT="$OUTCOME"
  export CAPAFY_TELEGRAM_SENDER="$FAKE_SENDER"
  export FAKE_MESSAGES FAKE_COUNT FAKE_SEND_OUTPUT
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
assert_has "real Telegram message id is recorded" "$record" '"telegram_message_id": "12345"'
rm -rf "$CASE_DIR"

echo "(D) FAIL reports blocker and next retry"
setup_case
seed_incident
retry='2026-08-01T18:00:00+09:00'
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
assert_has "FAIL contains next retry" "$body" "$retry"
rm -rf "$CASE_DIR"

echo "(E) missing message id never marks delivery complete"
setup_case
seed_incident
printf 'SUCCESS 2026-08-01T00:10:00Z patched code only\n' > "$STATE/.self-fix-capafy-loop.result"
FAKE_SEND_OUTPUT='TELEGRAM_SENT=false'
export FAKE_SEND_OUTPUT
bash "$MONITOR" >/dev/null 2>&1; rc=$?
record="$(incident_record)"
[ "$rc" -ne 0 ] && ok "sender without message id returns nonzero" || bad "sender without message id returns nonzero" "rc=$rc"
assert_has "delivery key remains null" "$record" '"terminal_message_key": null'
rm -rf "$CASE_DIR"

echo "=== capafy outcome monitor: $PASS passed $FAIL failed ==="
[ "$FAIL" -eq 0 ] || exit 1
