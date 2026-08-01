#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
HANDOFF="$ROOT/skills/self/capafy-loop/capafy-builder-handoff.sh"
DAILY="$ROOT/skills/self/capafy-loop/capafy-loop-daily.sh"
OUTCOME="$ROOT/skills/earn/capafy-marketing/scripts/capafy_outcome.py"
PASS=0; FAIL=0
ok(){ echo "  ok $1"; PASS=$((PASS+1)); }
bad(){ echo "  FAIL $1: $2"; FAIL=$((FAIL+1)); }
has(){ printf '%s' "$2" | grep -qF "$3" && ok "$1" || bad "$1" "missing '$3'"; }
not_has(){ printf '%s' "$2" | grep -qF "$3" && bad "$1" "unexpected '$3'" || ok "$1"; }
eq(){ [ "$2" = "$3" ] && ok "$1" || bad "$1" "want '$3', got '$2'"; }

setup_case(){
  T="$(mktemp -d)"; STATE="$T/state"; mkdir -p "$STATE"
  CANDIDATE="$T/builder-result.json"; REMOTE="$T/remote.json"; MONEY="$T/money.json"
  MESSAGES="$T/messages"; COUNT="$T/count"; FIX_CALLS="$T/fix-calls"
  printf '0\n' > "$COUNT"
  SENDER="$T/send.sh"
  printf '%s\n' '#!/usr/bin/env bash' \
    'n=$(cat "$COUNT"); printf "%s\n" "$((n+1))" > "$COUNT"' \
    'printf "%s\n" "$1" >> "$MESSAGES"' \
    'printf "TELEGRAM_SENT=true MSGID=5511\n"' > "$SENDER"
  chmod +x "$SENDER"
  FIXER="$T/self-fix.sh"
  printf '%s\n' '#!/usr/bin/env bash' \
    'printf "incident=%s loop=%s blocker=%s\n" "${CAPAFY_INCIDENT_ID:-}" "$1" "$2" >> "$FIX_CALLS"' > "$FIXER"
  chmod +x "$FIXER"
  printf '%s\n' '{"gross_usd":9.99,"pending_usd":8.0,"realized_usd":0.0,"mrr_usd":0.0,"cost_usd":4.777,"contribution_usd":-4.777}' > "$MONEY"
  export CAPAFY_OUTCOME_STATE_DIR="$STATE" CAPAFY_BUILDER_RESULT="$CANDIDATE"
  export CAPAFY_REMOTE_STATUS_JSON="$REMOTE" CAPAFY_MONEY_JSON="$MONEY"
  export CAPAFY_TELEGRAM_SENDER="$SENDER" CAPAFY_SELF_FIX="$FIXER" CAPAFY_OUTCOME_SCRIPT="$OUTCOME"
  export COUNT MESSAGES FIX_CALLS
}

seed_submitted(){
  printf '%s\n' '{"result":"submitted","agent_id":"9480246345","listing_url":"https://capafy.ai/developer/createAgent?source=temp-link&token=2082974745565622272&page=review"}' > "$CANDIDATE"
}

echo "(A) verified remote submission is the only Builder success"
setup_case; seed_submitted
printf '%s\n' '{"latest_version":{"agentId":"9480246345","status":1,"isConfirmedSkills":1,"isConfirmedConfigKeys":1,"title":"Portfolio Tracker — Daily Position Review"}}' > "$REMOTE"
bash "$HANDOFF" 0 "$T/evidence" >/dev/null 2>&1; rc=$?
body="$(cat "$MESSAGES" 2>/dev/null)"
eq "verified submission exits zero" "$rc" "0"
eq "verified submission sends once" "$(cat "$COUNT")" "1"
has "message contains agent id" "$body" "9480246345"
has "message contains remote state" "$body" "status 1; skill/config confirmed"
has "message contains review URL" "$body" "https://capafy.ai/developer/createAgent?source=temp-link&token=2082974745565622272&page=review"
has "terminal state records message id" "$(cat "$STATE/capafy-builder-terminal.json")" '"telegram_message_id": "5511"'
rm -rf "$T"

echo "(B) runner rc=0 without verified remote readback is failure"
setup_case; seed_submitted
printf '%s\n' '{"latest_version":{"agentId":"9480246345","status":0,"isConfirmedSkills":1,"isConfirmedConfigKeys":0,"title":"Portfolio Tracker — Daily Position Review"}}' > "$REMOTE"
bash "$HANDOFF" 0 "$T/evidence" >/dev/null 2>&1; rc=$?
[ "$rc" -ne 0 ] && ok "unverified remote state returns nonzero" || bad "unverified remote state returns nonzero" "rc=$rc"
fix="$(cat "$FIX_CALLS")"
has "failure starts incident-aware self-fix" "$fix" "incident=capafy-builder-"
has "failure targets normalized Capafy loop" "$fix" "loop=capafy"
rm -rf "$T"

echo "(C) runner failure starts or reuses one incident"
setup_case
printf '%s\n' '{"result":"failure","reason":"browser lease unavailable"}' > "$CANDIDATE"
bash "$HANDOFF" 9 "$T/evidence" >/dev/null 2>&1 || true
bash "$HANDOFF" 9 "$T/evidence" >/dev/null 2>&1 || true
eq "same failure invokes one active self-fix chain" "$(wc -l < "$FIX_CALLS" | tr -d ' ')" "1"
eq "same failure creates one incident record" "$(find "$STATE/capafy-incidents" -name '*.json' | wc -l | tr -d ' ')" "1"
rm -rf "$T"

echo "(D) bounded no-op is honest and not revenue"
setup_case
printf '%s\n' '{"result":"no-op","reason":"publish cap full; no safe slot available"}' > "$CANDIDATE"
bash "$HANDOFF" 0 "$T/evidence" >/dev/null 2>&1; rc=$?
body="$(cat "$MESSAGES")"
eq "bounded no-op exits zero" "$rc" "0"
has "no-op is named" "$body" "completed without a new submission"
has "no-op preserves zero realized revenue" "$body" 'Realized bank payout: $0.00'
not_has "no-op never claims submitted" "$body" "submitted and verified"
rm -rf "$T"

echo "(E) daily loop exposes deterministic reporting ownership"
probe="$(CAPAFY_LOOP_REPORTING_PROBE_ONLY=1 bash "$DAILY")"
has "shell owns terminal classification" "$probe" "terminal_owner=capafy-builder-handoff.sh"
has "agent Telegram is disabled" "$probe" "agent_telegram=false"

echo "=== capafy builder outcome: $PASS passed $FAIL failed ==="
[ "$FAIL" -eq 0 ] || exit 1
