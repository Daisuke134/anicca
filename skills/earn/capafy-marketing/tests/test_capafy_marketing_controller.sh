#!/usr/bin/env bash
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="$(cd "$HERE/../../../.." && pwd)"
DAILY="$ROOT/skills/earn/capafy-marketing/capafy-ig-marketing-daily.sh"; LIFECYCLE="$ROOT/skills/earn/capafy-marketing/scripts/capafy_ig_lifecycle.py"
P=0 F=0
ok(){ P=$((P+1)); echo "  ok $1"; }
bad(){ F=$((F+1)); echo "  not ok $1"; }
eq(){ [ "$2" = "$3" ] && ok "$1" || bad "$1 got=$2 want=$3"; }
has(){ grep -Fq -- "$3" "$2" && ok "$1" || bad "$1 missing=$3"; }
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT; mkdir -p "$T/bin"
cat >"$T/bin/browser" <<'SH'
#!/usr/bin/env bash
echo http://127.0.0.1:9555
SH
cat >"$T/bin/runner" <<'SH'
#!/usr/bin/env bash
echo "$*" >>"$RUN_CALLS"; cat >/dev/null
python3 - "$CAPAFY_CREATIVE_CANDIDATE" "$MEDIA" "${CANDIDATE_MODE:-valid}" <<'PY'
import json,sys
p,m,mode=sys.argv[1:];d={"schema_version":1,"title":"Portfolio Tracker","agent_id":"9480246345","listing_url":"https://capafy.ai/agent/9480246345","campaign_url":"https://capafy-skills-daily.netlify.app/go/9480246345?utm_source=instagram&utm_medium=reel&utm_campaign=portfolio-tracker-launch","caption":"Your portfolio changed today.","media_path":m,"commercial_intent":False}
if mode=="commercial":d["commercial_intent"]=True
if mode=="missing":d.pop("campaign_url")
if mode=="foreign":d.update(agent_id="1657185274",listing_url="https://capafy.ai/agent/1657185274")
json.dump(d,open(p,"w"))
PY
SH
cat >"$T/bin/selector" <<'SH'
#!/usr/bin/env bash
echo call >>"$SELECT_CALLS"
echo '{"ok":true,"agent_id":"9480246345","name":"Portfolio Tracker","desc":"Review fresh positions across fixed dimensions.","url":"https://capafy.ai/agent/9480246345","online_pool":27}'
SH
cat >"$T/bin/poster" <<'SH'
#!/usr/bin/env bash
echo "$*" >>"$POST_CALLS"
case "${POSTER_MODE:-published}" in
 challenge) echo '{"status":"challenge","published":false}'; exit 2;;
 dry) echo '{"status":"dry_verified","published":false}';;
 unverified) echo '{"status":"published_verified","published":true,"reel_url":"https://www.instagram.com/reel/NEW456/","owner_session_verified":false}';;
 *) echo '{"status":"published_verified","published":true,"reel_url":"https://www.instagram.com/reel/NEW456/","owner_session_verified":true}';;
esac
SH
cat >"$T/bin/sender" <<'SH'
#!/usr/bin/env bash
echo "$1" >>"$MESSAGES"; echo MSGID=8001
SH
cat >"$T/bin/launchctl" <<'SH'
#!/usr/bin/env bash
echo "$*" >>"$KICKS"
SH
cat >"$T/bin/guard" <<'SH'
#!/usr/bin/env bash
echo "$*" >>"$GUARD_CALLS"
SH
chmod +x "$T/bin/"*
case_setup(){
 C="$T/$1"; mkdir -p "$C/home/.cloak" "$C/state"; echo '[]' >"$C/accounts"
 : >"$C/runs"; : >"$C/posts"; : >"$C/messages"; : >"$C/kicks"; : >"$C/guard.calls"
 MEDIA="$C/reel.mp4"; printf '\0\0\0\30ftypmp42fixture' >"$MEDIA"
 export HOME="$C/home" CAPAFY_IG_ACCOUNTS_FILE="$C/accounts" CAPAFY_IG_LIFECYCLE_STATE="$C/state/lifecycle.json" CAPAFY_OUTCOME_STATE_DIR="$C/state"
 export CAPAFY_MARKETING_RESULT="$C/state/result.json" CAPAFY_CREATIVE_CANDIDATE="$C/state/candidate.json" CAPAFY_RUN_AGENT="$T/bin/runner" CAPAFY_REEL_POSTER="$T/bin/poster"
 export CAPAFY_LISTING_SELECTOR="$T/bin/selector" SELECT_CALLS="$C/select.calls"; : >"$SELECT_CALLS"
 export CAPAFY_MARKETING_BROWSER="$T/bin/browser" CAPAFY_TELEGRAM_SENDER="$T/bin/sender" CAPAFY_LAUNCHCTL="$T/bin/launchctl" CAPAFY_IG_LIFECYCLE="$LIFECYCLE"
 export CAPAFY_BROWSER_GUARD="$T/bin/guard" GUARD_CALLS="$C/guard.calls"
 export CAPAFY_IG_TID=tab-1 CAPAFY_MARKETING_MODE=live RUN_CALLS="$C/runs" POST_CALLS="$C/posts" MESSAGES="$C/messages" KICKS="$C/kicks" MEDIA
 unset CANDIDATE_MODE POSTER_MODE
}
active(){ python3 - "$CAPAFY_IG_ACCOUNTS_FILE" <<'PY'
import json,sys
json.dump([{"handle":"capafy.skills25042","status":"warming","session_owner":"browser","browser_identity":"instagram:capafy-provision","port":9555,"created":"2026-08-01"}],open(sys.argv[1],"w"))
PY
}
case_setup needed; bash "$DAILY" >/dev/null 2>&1
eq "needed does not call creative" "$(wc -l <"$RUN_CALLS" | tr -d ' ')" 0; eq "needed wakes manager" "$(wc -l <"$KICKS" | tr -d ' ')" 1
case_setup immediate; active; export CAPAFY_MARKETING_MODE=dry POSTER_MODE=dry; bash "$DAILY" >/dev/null 2>&1
eq "verified session immediately calls creative" "$(wc -l <"$RUN_CALLS" | tr -d ' ')" 1; has "immediate probe reaches poster" "$POST_CALLS" "--expected-capability publish_probe"
eq "immediate probe selects from seller inventory" "$(wc -l <"$SELECT_CALLS" | tr -d ' ')" 1
case_setup foreign; active; export CANDIDATE_MODE=foreign; bash "$DAILY" >/dev/null 2>&1; rc=$?
[ "$rc" -ne 0 ] && ok "foreign public listing refused" || bad "foreign public listing accepted"; eq "foreign listing not posted" "$(wc -l <"$POST_CALLS" | tr -d ' ')" 0
eq "foreign failure releases browser lease" "$(grep -Fc 'release instagram:capafy-provision' "$GUARD_CALLS")" 1
case_setup commercial; active; export CANDIDATE_MODE=commercial; bash "$DAILY" >/dev/null 2>&1; rc=$?
[ "$rc" -ne 0 ] && ok "commercial candidate refused" || bad "commercial candidate accepted"; eq "commercial candidate not posted" "$(wc -l <"$POST_CALLS" | tr -d ' ')" 0
case_setup missing; active; export CANDIDATE_MODE=missing; bash "$DAILY" >/dev/null 2>&1; rc=$?
[ "$rc" -ne 0 ] && ok "missing candidate field refused" || bad "missing field accepted"; eq "missing candidate not posted" "$(wc -l <"$POST_CALLS" | tr -d ' ')" 0
case_setup dry; active; export CAPAFY_MARKETING_MODE=dry POSTER_MODE=dry; bash "$DAILY" >/dev/null 2>&1
eq "ready calls marketing agent" "$(grep -Fc -- '--task-class marketing-agent' "$RUN_CALLS")" 1; has "dry calls poster dry" "$POST_CALLS" "--dry"; has "dry never claims published" "$MESSAGES" "not posted"
case_setup live; active; bash "$DAILY" >/dev/null 2>&1; eq "live terminal succeeds" "$?" 0
has "live reports verified Reel" "$MESSAGES" "https://www.instagram.com/reel/NEW456/"; eq "live records Reel" "$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["last_public_reel_url"])' "$CAPAFY_IG_LIFECYCLE_STATE")" https://www.instagram.com/reel/NEW456/
eq "live records owner session proof" "$(python3 -c 'import json,sys;print(str(json.load(open(sys.argv[1]))["post_write_session_verified"]).lower())' "$CAPAFY_IG_LIFECYCLE_STATE")" true
eq "successful pass releases browser lease" "$(grep -Fc 'release instagram:capafy-provision' "$GUARD_CALLS")" 1
case_setup unverified; active; export POSTER_MODE=unverified; bash "$DAILY" >/dev/null 2>&1; rc=$?
[ "$rc" -ne 0 ] && ok "missing owner proof fails terminal" || bad "missing owner proof accepted"; recorded_unverified="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("last_public_reel_url") or "")' "$CAPAFY_IG_LIFECYCLE_STATE" 2>/dev/null || true)"; [ -z "$recorded_unverified" ] && ok "unverified owner records no Reel" || bad "unverified owner recorded Reel"
case_setup challenge; active; export POSTER_MODE=challenge; bash "$DAILY" >/dev/null 2>&1; rc=$?
[ "$rc" -ne 0 ] && ok "poster challenge fails terminal" || bad "challenge accepted"; eq "poster challenge retires account" "$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))[0]["status"])' "$CAPAFY_IG_ACCOUNTS_FILE")" session_failed; eq "poster challenge wakes manager" "$(wc -l <"$KICKS" | tr -d ' ')" 1
echo "=== test_capafy_marketing_controller: $P passed $F failed ==="; [ "$F" -eq 0 ]
