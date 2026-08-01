#!/usr/bin/env bash
# Deterministic Capafy creative -> browser publish -> P0 outcome controller.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:${PATH:-}"
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "${CAPAFY_IG_REPORTING_PROBE_ONLY:-0}" = "1" ]; then
  printf 'terminal_owner=capafy-marketing-handoff.sh agent_telegram=false\n'; exit 0
fi
export ANICCA_BUDGET_SCOPE_ID="${CAPAFY_MARKETING_PASS_ID:-$(date +%s)-$$}"
export ANICCA_PASS_TOKEN_BUDGET="${CAPAFY_MARKETING_PASS_TOKEN_BUDGET:-1048576}"
export ANICCA_LOOP_DAILY_TOKEN_BUDGET="${CAPAFY_MARKETING_DAILY_TOKEN_BUDGET:-2097152}"
export ANICCA_BUDGET_DAILY_SCOPE="${CAPAFY_MARKETING_BUDGET_DAILY_SCOPE:-capafy-ig-marketing-daily}"
export ANICCA_TOKEN_BUDGET_LEDGER="${CAPAFY_TOKEN_BUDGET_LEDGER:-$HOME/.local/state/anicca/telemetry/token-budget.jsonl}"
. "$HERE/account_state.sh"
ENGINE="$HERE/../marketing-engine"
RUN_AGENT="${CAPAFY_RUN_AGENT:-$ENGINE/run_agent.sh}"
LIFECYCLE="${CAPAFY_IG_LIFECYCLE:-$HERE/scripts/capafy_ig_lifecycle.py}"
POSTER="${CAPAFY_REEL_POSTER:-$HERE/scripts/capafy_reel_poster.py}"
SELECTOR="${CAPAFY_LISTING_SELECTOR:-$HERE/scripts/select_listing.py}"
BROWSER="${CAPAFY_MARKETING_BROWSER:-$HERE/../../browser/ensure_provision_browser.sh}"
HANDOFF="${CAPAFY_MARKETING_HANDOFF:-$HERE/capafy-marketing-handoff.sh}"
KICKSTART="${CAPAFY_LAUNCHCTL:-launchctl}"
ACCOUNTS="${CAPAFY_IG_ACCOUNTS_FILE:-$(capafy_ig_accounts_file)}"
STATE_DIR="${CAPAFY_OUTCOME_STATE_DIR:-$HOME/.openclaw/state}"
STATE="${CAPAFY_IG_LIFECYCLE_STATE:-$STATE_DIR/capafy-ig-lifecycle.json}"
RESULT="${CAPAFY_MARKETING_RESULT:-$STATE_DIR/capafy-marketing-result.json}"
CANDIDATE="${CAPAFY_CREATIVE_CANDIDATE:-$STATE_DIR/capafy-marketing-creative.json}"
MODE="${CAPAFY_MARKETING_MODE:-live}"
if [ "${CAPAFY_IG_PROBE_ONLY:-0}" = "1" ]; then
  probe_handle="$(resolve_capafy_ig_handle "$ACCOUNTS")"
  if [ -n "$probe_handle" ]; then
    printf 'active_handle=%s lifecycle_owner=controller\n' "$probe_handle"
  else
    printf 'active_handle=none lifecycle_owner=account-manager\n'
  fi
  exit 0
fi
case "$MODE" in dry|live) ;; *) printf 'invalid CAPAFY_MARKETING_MODE=%s\n' "$MODE" >&2; exit 2;; esac
mkdir -p "$STATE_DIR"
# Crash recovery: delivery may succeed immediately before lifecycle bookkeeping.
# Reconcile that exact receipt without creating or sharing a second Reel.
if [ -f "$RESULT" ] && [ -f "$STATE" ] && [ "$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("result",""))' "$RESULT" 2>/dev/null)" = published ]; then
  pending_reel="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("reel_url",""))' "$RESULT")"
  pending_handle="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("handle", "") or json.load(open(sys.argv[2])).get("handle", ""))' "$RESULT" "$STATE" 2>/dev/null || true)"
  recorded_reel="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("last_public_reel_url","") or "")' "$STATE" 2>/dev/null || true)"
  pending_owner="$(python3 -c 'import json,sys;print(str(json.load(open(sys.argv[1])).get("owner_session_verified",False)).lower())' "$RESULT" 2>/dev/null || true)"
  if [ -n "$pending_reel" ] && [ -n "$pending_handle" ] && [ "$pending_owner" = true ]; then
    if [ "$pending_reel" != "$recorded_reel" ]; then
      python3 "$LIFECYCLE" record-reel --state "$STATE" --handle "$pending_handle" --reel-url "$pending_reel" --owner-session-verified >/dev/null || exit 2
    fi
    CAPAFY_MARKETING_RESULT="$RESULT" bash "$HANDOFF" 0 recovery || exit $?
    rm -f "$RESULT"; exit 0
  fi
fi
rm -f "$RESULT" "$CANDIDATE"
fail(){
  python3 - "$RESULT" "$1" <<'PY'
import json,sys
json.dump({"result":"failure","reason":sys.argv[2]},open(sys.argv[1],"w"))
PY
  CAPAFY_MARKETING_RESULT="$RESULT" bash "$HANDOFF" 1 controller
  exit $?
}
handle="$(resolve_capafy_ig_handle "$ACCOUNTS")"
python3 "$LIFECYCLE" snapshot --accounts "$ACCOUNTS" --state "$STATE" >/dev/null || fail "could not derive marketing lifecycle state"
replacement="$(python3 -c 'import json,sys;print(str(json.load(open(sys.argv[1]))["replacement_requested"]).lower())' "$STATE")"
if [ "$replacement" = true ]; then
  "$KICKSTART" kickstart -k "gui/$(id -u)/ai.anicca.capafy-ig-account-manager" >/dev/null 2>&1 || true
  exit 0
fi
status="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["status"])' "$STATE")"
capability="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["capability"])' "$STATE")"
[ "$capability" = publish_probe ] || fail "unsupported marketing capability in state $status: $capability"
identity="$(_resolve_capafy_ig_account_field "$ACCOUNTS" browser_identity)"; [ -n "$identity" ] || fail "active account has no browser identity"
cdp="$(bash "$BROWSER" "$identity")" || fail "active account browser did not start"; port="${cdp##*:}"
case "$port" in ''|*[!0-9]*) fail "active browser returned no numeric port";; esac
tid="${CAPAFY_IG_TID:-}"
if [ -z "$tid" ]; then
  tid="$(python3 - "$port" <<'PY'
import json,sys,urllib.request
tabs=json.load(urllib.request.urlopen(f"http://127.0.0.1:{sys.argv[1]}/json/list",timeout=8));print(next((x["id"] for x in tabs if x.get("type")=="page" and "instagram.com" in x.get("url","")),""))
PY
)"
fi
[ -n "$tid" ] || fail "active Instagram browser tab is missing"
if [ -x "$SELECTOR" ]; then
  selection_raw="$("$SELECTOR" 2>&1)"; selection_rc=$?
else
  selection_raw="$(python3 "$SELECTOR" 2>&1)"; selection_rc=$?
fi
[ "$selection_rc" -eq 0 ] || fail "owned listing selector failed"
selection="$(python3 - "$selection_raw" <<'PY'
import json,sys,urllib.parse
d=json.loads(sys.argv[1]); required=("agent_id","name","desc","url")
if d.get("ok") is not True or any(d.get(k) in (None,"") for k in required): raise SystemExit(2)
aid=str(d["agent_id"]); u=urllib.parse.urlparse(str(d["url"]))
if u.scheme!="https" or (u.hostname or "") not in {"capafy.ai","www.capafy.ai"} or u.path.rstrip("/")!=f"/agent/{aid}": raise SystemExit(2)
print(json.dumps({k:d[k] for k in required},ensure_ascii=False,separators=(",",":")))
PY
)" || fail "owned listing selector returned invalid evidence"
prompt="Create one original product-education 9:16 MP4 plus exact caption for the seller-owned Capafy listing in this JSON: $selection
Use exactly this listing; do not search for or substitute another public Capafy agent.
This first publish probe is low-pressure: no hard offer CTA and no bio-link mutation.
Write one creative candidate JSON to $CANDIDATE with schema_version, title, agent_id,
listing_url, campaign_url, caption, media_path, and commercial_intent=false.
Do not provision accounts, warm sessions, publish, verify publication, or send Telegram."
evidence="$STATE_DIR/agent-runner-evidence/capafy-ig-marketing/$(date +%s)-$$"
CAPAFY_CREATIVE_CANDIDATE="$CANDIDATE" printf '%s\n' "$prompt" | "$RUN_AGENT" --task-class marketing-agent --evidence-dir "$evidence" --task-label capafy-ig-marketing-daily --loop capafy >/dev/null 2>&1 || fail "creative agent did not complete"
[ -f "$CANDIDATE" ] || fail "creative agent wrote no candidate"
normalized="$(python3 - "$CANDIDATE" "$selection" <<'PY'
import json,pathlib,sys,urllib.parse
d=json.load(open(sys.argv[1])); selected=json.loads(sys.argv[2]); required=("schema_version","title","agent_id","listing_url","campaign_url","caption","media_path","commercial_intent")
missing=[x for x in required if x not in d or d[x] in (None,"")]
if missing: raise SystemExit("missing candidate fields: "+",".join(missing))
u=urllib.parse.urlparse(str(d["listing_url"]));
if u.scheme!="https" or not ((u.hostname or "")=="capafy.ai" or (u.hostname or "").endswith(".capafy.ai")): raise SystemExit("listing_url is not Capafy")
if d["commercial_intent"] is not False: raise SystemExit("commercial creative is forbidden")
if not pathlib.Path(d["media_path"]).is_file(): raise SystemExit("media_path is missing")
aid=str(d["agent_id"])
if u.path.rstrip("/")!=f"/agent/{aid}": raise SystemExit("listing_url does not match agent_id")
if aid!=str(selected["agent_id"]) or str(d["listing_url"]).rstrip("/")!=str(selected["url"]).rstrip("/"): raise SystemExit("candidate is not the seller-owned selected listing")
if str(d["title"]).strip()!=str(selected["name"]).strip(): raise SystemExit("candidate title does not match the seller listing")
d["campaign_url"]=f"https://capafy-skills-daily.netlify.app/go/{urllib.parse.quote(aid,safe='')}?utm_source=instagram&utm_medium=reel&utm_campaign=capafy-skill"
print(json.dumps(d))
PY
)" || fail "creative candidate failed the original publish-probe evidence contract"
caption_file="$STATE_DIR/capafy-caption.txt"; printf '%s' "$(python3 -c 'import json,sys;print(json.loads(sys.argv[1])["caption"])' "$normalized")" >"$caption_file"
video="$(python3 -c 'import json,sys;print(json.loads(sys.argv[1])["media_path"])' "$normalized")"
mode_flag=--live; [ "$MODE" = dry ] && mode_flag=--dry
if [ -x "$POSTER" ]; then
  poster_json="$("$POSTER" --video "$video" --caption-file "$caption_file" --handle "$handle" --port "$port" --tid "$tid" --expected-capability "$capability" "$mode_flag" 2>&1)"; poster_rc=$?
else
  poster_json="$(python3 "$POSTER" --video "$video" --caption-file "$caption_file" --handle "$handle" --port "$port" --tid "$tid" --expected-capability "$capability" "$mode_flag" 2>&1)"; poster_rc=$?
fi
poster_status="$(python3 -c 'import json,sys;print(json.loads(sys.argv[1]).get("status","invalid"))' "$poster_json" 2>/dev/null || echo invalid)"
if [ "$poster_status" = challenge ]; then
  printf '%s\n' "{\"result\":\"challenge\",\"handle\":\"$handle\",\"reason\":\"browser poster reached an Instagram challenge\",\"next_retry_at\":\"immediately\"}" >"$RESULT"
  CAPAFY_MARKETING_RESULT="$RESULT" bash "$HANDOFF" 1 "$evidence"; exit $?
fi
[ "$poster_rc" -eq 0 ] || fail "Reel poster failed: $poster_status"
python3 - "$RESULT" "$normalized" "$poster_json" "$MODE" <<'PY'
import json,sys
p,candidate_raw,poster_raw,mode=sys.argv[1:];c=json.loads(candidate_raw);r=json.loads(poster_raw)
if mode=="dry":
 if r.get("status")!="dry_verified" or r.get("published"): raise SystemExit(2)
 out={"result":"dry",**{k:c[k] for k in ("title","agent_id","listing_url","caption","media_path")}}
else:
 if r.get("status")!="published_verified" or r.get("published") is not True or not r.get("reel_url") or r.get("owner_session_verified") is not True: raise SystemExit(2)
 out={"result":"published",**{k:c[k] for k in ("title","agent_id","listing_url","campaign_url","caption","media_path")},"reel_url":r["reel_url"],"owner_session_verified":True}
json.dump(out,open(p,"w"))
PY
[ -f "$RESULT" ] || fail "poster result could not produce a terminal outcome"
if [ "$MODE" = live ]; then
  reel="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["reel_url"])' "$RESULT")"
  python3 "$LIFECYCLE" record-reel --state "$STATE" --handle "$handle" --reel-url "$reel" --owner-session-verified >/dev/null || exit 2
fi
CAPAFY_MARKETING_RESULT="$RESULT" bash "$HANDOFF" 0 "$evidence" || exit $?
rm -f "$RESULT"
exit 0
