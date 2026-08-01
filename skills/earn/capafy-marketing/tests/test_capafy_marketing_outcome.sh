#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
HANDOFF="$ROOT/skills/earn/capafy-marketing/capafy-marketing-handoff.sh"
DAILY="$ROOT/skills/earn/capafy-marketing/capafy-ig-marketing-daily.sh"
OUTCOME="$ROOT/skills/earn/capafy-marketing/scripts/capafy_outcome.py"
P=0; F=0
ok(){ echo "  ok $1"; P=$((P+1)); }; bad(){ echo "  FAIL $1: $2"; F=$((F+1)); }
has(){ printf '%s' "$2"|grep -qiF "$3"&&ok "$1"||bad "$1" "missing '$3'"; }
not_has(){ printf '%s' "$2"|grep -qiF "$3"&&bad "$1" "unexpected '$3'"||ok "$1"; }
eq(){ [ "$2" = "$3" ]&&ok "$1"||bad "$1" "want '$3' got '$2'"; }

setup_case(){
  T="$(mktemp -d)"; STATE="$T/state"; mkdir -p "$STATE"
  RESULT="$T/result.json"; MSG="$T/messages"; COUNT="$T/count"; MEDIA="$T/reel.mp4"
  printf 'video' > "$MEDIA"; printf '0\n' > "$COUNT"
  SENDER="$T/send.sh"; printf '%s\n' '#!/usr/bin/env bash' \
    'n=$(cat "$COUNT"); printf "%s\n" "$((n+1))" > "$COUNT"' \
    'printf "%s\n" "$1" >> "$MSG"' 'printf "TELEGRAM_SENT=true MSGID=6611\n"' > "$SENDER"; chmod +x "$SENDER"
  export CAPAFY_OUTCOME_STATE_DIR="$STATE" CAPAFY_MARKETING_RESULT="$RESULT"
  export CAPAFY_TELEGRAM_SENDER="$SENDER" CAPAFY_OUTCOME_SCRIPT="$OUTCOME" COUNT MSG
}

echo "(A) scheduler loaded without URL is scheduled, not published"
setup_case
printf '%s\n' '{"result":"scheduled","handle":"capafy.skills10491","reason":"scheduler loaded; no verified post in this pass"}' > "$RESULT"
bash "$HANDOFF" 0 "$T/evidence" >/dev/null 2>&1; rc=$?; body="$(cat "$MSG")"
eq "scheduled terminal exits zero" "$rc" "0"
has "scheduled state is explicit" "$body" "scheduler is loaded"
has "missing post is explicit" "$body" "no public post is verified"
not_has "scheduled is not published" "$body" "Reel published"
not_has "scheduled is not live" "$body" "live"
rm -rf "$T"

echo "(B) dry creative is visible but never claims public posting"
setup_case
python3 - "$RESULT" "$MEDIA" <<'PY'
import json,sys
json.dump({"result":"dry","title":"Portfolio Tracker — Daily Position Review","agent_id":"9480246345","listing_url":"https://capafy.ai/agent/9480246345","caption":"Your portfolio changed today.","media_path":sys.argv[2]},open(sys.argv[1],"w"))
PY
bash "$HANDOFF" 0 "$T/evidence" >/dev/null 2>&1; body="$(cat "$MSG")"
has "dry state is explicit" "$body" "DRY creative — not posted"
has "dry includes caption" "$body" "Your portfolio changed today."
has "dry includes media artifact" "$body" "$MEDIA"
not_has "dry does not claim Reel publication" "$body" "Reel published"
rm -rf "$T"

echo "(C) public success requires every evidence field"
setup_case
python3 - "$RESULT" "$MEDIA" <<'PY'
import json,sys
json.dump({"result":"published","title":"Portfolio Tracker — Daily Position Review","agent_id":"9480246345","reel_url":"https://www.instagram.com/reel/REAL123/","listing_url":"https://capafy.ai/agent/9480246345","campaign_url":"https://capafy-skills-daily.netlify.app/go/9480246345?utm_source=instagram&utm_medium=reel","caption":"Your portfolio changed today.","media_path":sys.argv[2]},open(sys.argv[1],"w"))
PY
bash "$HANDOFF" 0 "$T/evidence" >/dev/null 2>&1; rc=$?; body="$(cat "$MSG")"
eq "published evidence exits zero" "$rc" "0"
has "published contains Reel URL" "$body" "https://www.instagram.com/reel/REAL123/"
has "published contains skill URL" "$body" "https://capafy.ai/agent/9480246345"
has "published contains campaign URL" "$body" "utm_medium=reel"
has "published contains media artifact" "$body" "$MEDIA"
rm -rf "$T"

echo "(D) challenge is an account lifecycle incident, not a ban claim"
setup_case
printf '%s\n' '{"result":"challenge","handle":"capafy.skills10491","reason":"ChallengeRequired while establishing posting session","next_retry_at":"2026-08-01T18:00:00+09:00"}' > "$RESULT"
bash "$HANDOFF" 1 "$T/evidence" >/dev/null 2>&1 || true; body="$(cat "$MSG")"
has "challenge is named" "$body" "platform challenge"
has "replacement lifecycle is next" "$body" "replacement-account workflow"
not_has "challenge does not assert ban" "$body" "banned"
eq "challenge creates one incident" "$(find "$STATE/capafy-incidents" -name '*.json'|wc -l|tr -d ' ')" "1"
rm -rf "$T"

echo "(E) 180-second runner timeout is technical, not account health"
setup_case
printf '%s\n' '{"result":"failure","reason":"agent runner timed out at 180 seconds"}' > "$RESULT"
bash "$HANDOFF" 124 "$T/evidence" >/dev/null 2>&1 || true; body="$(cat "$MSG")"
has "timeout is reported" "$body" "timed out at 180 seconds"
not_has "timeout does not assert ban" "$body" "banned"
not_has "timeout does not assert poisoned account" "$body" "poisoned"
rm -rf "$T"

echo "(F) daily loop exposes deterministic terminal ownership"
probe="$(CAPAFY_IG_REPORTING_PROBE_ONLY=1 CAPAFY_IG_PROBE_ONLY=1 bash "$DAILY")"
has "marketing shell owns terminal" "$probe" "terminal_owner=capafy-marketing-handoff.sh"
has "agent Telegram disabled" "$probe" "agent_telegram=false"

echo "=== capafy marketing outcome: $P passed $F failed ==="; [ "$F" -eq 0 ] || exit 1
