#!/usr/bin/env bash
# Browser-owned warmup adapter; calendar age never grants a capability.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:${PATH:-}"
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/account_state.sh"
ACCOUNTS="${CAPAFY_IG_ACCOUNTS_FILE:-$(capafy_ig_accounts_file)}"
STATE_DIR="${CAPAFY_OUTCOME_STATE_DIR:-$HOME/.openclaw/state}"
STATE="${CAPAFY_IG_LIFECYCLE_STATE:-$STATE_DIR/capafy-ig-lifecycle.json}"
RESULT="${CAPAFY_MARKETING_RESULT:-$STATE_DIR/capafy-warmup-result.json}"
LIFECYCLE="${CAPAFY_IG_LIFECYCLE:-$HERE/scripts/capafy_ig_lifecycle.py}"
HANDOFF="${CAPAFY_MARKETING_HANDOFF:-$HERE/capafy-marketing-handoff.sh}"
BROWSER="${CAPAFY_WARMUP_BROWSER:-$HERE/../../browser/ensure_provision_browser.sh}"
WARM="${CAPAFY_WARMUP_RUNNER:-$HOME/.agents/skills/ig-account-warmer/scripts/warm.py}"
KICKSTART="${CAPAFY_LAUNCHCTL:-launchctl}"
JITTER_MAX_SECONDS="${CAPAFY_WARMUP_JITTER_MAX_SECONDS:-10800}"
mkdir -p "$STATE_DIR"
[ "$JITTER_MAX_SECONDS" -gt 0 ] && sleep $((RANDOM % (JITTER_MAX_SECONDS + 1)))
handle="$(resolve_capafy_ig_handle "$ACCOUNTS")"
empty="$STATE_DIR/capafy-empty-warmup.json"; [ -f "$empty" ] || printf '{"log":[]}\n' >"$empty"
if [ -z "$handle" ]; then
  python3 "$LIFECYCLE" snapshot --accounts "$ACCOUNTS" --warmup "$empty" --state "$STATE" >/dev/null || exit 2
  "$KICKSTART" kickstart -k "gui/$(id -u)/ai.anicca.capafy-ig-account-manager" >/dev/null 2>&1 || true
  exit 0
fi
warmup="$HOME/.cloak/ig-warmup-$handle.json"; [ -f "$warmup" ] || printf '{"log":[]}\n' >"$warmup"
python3 "$LIFECYCLE" snapshot --accounts "$ACCOUNTS" --warmup "$warmup" --state "$STATE" >/dev/null || exit 2
before_status="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["status"])' "$STATE")"
before_count="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["warmup_successes"])' "$STATE")"
identity="$(_resolve_capafy_ig_account_field "$ACCOUNTS" browser_identity)"
[ -n "$identity" ] || exit 2
cdp="$(bash "$BROWSER" "$identity")" || exit 2; port="${cdp##*:}"
case "$port" in ''|*[!0-9]*) exit 2;; esac
if [ -x "$WARM" ]; then
  warm_output="$(CDP_PORT="$port" "$WARM" "$handle" 2>&1)"; warm_rc=$?
else
  warm_output="$(CDP_PORT="$port" /opt/homebrew/bin/python3 "$WARM" "$handle" 2>&1)"; warm_rc=$?
fi
python3 "$LIFECYCLE" snapshot --accounts "$ACCOUNTS" --warmup "$warmup" --state "$STATE" >/dev/null || exit 2
after_status="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["status"])' "$STATE")"
after_count="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["warmup_successes"])' "$STATE")"
replacement="$(python3 -c 'import json,sys;print(str(json.load(open(sys.argv[1]))["replacement_requested"]).lower())' "$STATE")"
if [ "$replacement" = true ]; then
  python3 - "$RESULT" "$handle" "$warm_output" <<'PY'
import json,sys
json.dump({"result":"replacement_waiting","handle":sys.argv[2],"reason":sys.argv[3][:500],"next_retry_at":"immediately"},open(sys.argv[1],"w"))
PY
  CAPAFY_MARKETING_RESULT="$RESULT" bash "$HANDOFF" 1 warmup
  exit $?
fi
if [ "$warm_rc" -ne 0 ] || [ "$after_count" -le "$before_count" ]; then
  case "$warm_output" in *'already warmed today'*) exit 0;; esac
  python3 - "$RESULT" "$warm_rc" <<'PY'
import json,sys
json.dump({"result":"failure","reason":f"browser warmup produced no new verified action evidence (rc={sys.argv[2]})"},open(sys.argv[1],"w"))
PY
  CAPAFY_MARKETING_RESULT="$RESULT" bash "$HANDOFF" 1 warmup
  exit $?
fi
[ "$after_status" = "$before_status" ] && exit 0
python3 - "$RESULT" "$STATE" "$before_status" <<'PY'
import json,sys
s=json.load(open(sys.argv[2]));json.dump({"result":"lifecycle_progress","handle":s["handle"],"before_status":sys.argv[3],"status":s["status"],"warmup_successes":s["warmup_successes"],"capability":s["capability"],"public_post_url":None,"next_action":"create the first non-commercial Reel" if s["capability"]=="noncommercial_post" else "run the next automatic verified browser warmup"},open(sys.argv[1],"w"))
PY
CAPAFY_MARKETING_RESULT="$RESULT" bash "$HANDOFF" 0 warmup || exit $?
rm -f "$RESULT"
exit 0
