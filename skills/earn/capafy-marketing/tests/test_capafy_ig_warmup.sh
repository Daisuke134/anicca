#!/usr/bin/env bash
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../../.." && pwd)"
WARMUP="$ROOT/skills/earn/capafy-marketing/warm_jitter.sh"
LIFECYCLE="$ROOT/skills/earn/capafy-marketing/scripts/capafy_ig_lifecycle.py"
P=0 F=0
ok(){ P=$((P+1)); echo "  ok $1"; }
bad(){ F=$((F+1)); echo "  not ok $1"; }
eq(){ [ "$2" = "$3" ] && ok "$1" || bad "$1 got=$2 want=$3"; }
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
mkdir -p "$T/bin"
cat >"$T/bin/browser" <<'SH'
#!/usr/bin/env bash
echo http://127.0.0.1:9555
SH
cat >"$T/bin/warm" <<'SH'
#!/usr/bin/env bash
echo call >>"$WARM_CALLS"
h="$1"; p="$HOME/.cloak/ig-warmup-$h.json"; mkdir -p "$(dirname "$p")"
python3 - "$p" "${FAKE_WARM_MODE:-success}" "${FAKE_DATE:-2026-08-01}" <<'PY'
import json,sys
p,mode,date=sys.argv[1:]
try:d=json.load(open(p))
except:d={"log":[]}
if mode=="noevidence": print("{}")
elif mode=="skip": print(json.dumps({"skip":"already warmed today"}))
elif mode=="abort":
 d.setdefault("aborts",[]).append({"date":date,"ABORT":"not logged in"});json.dump(d,open(p,"w"));print('{"ABORT":"not logged in"}')
else:
 d["log"]=[x for x in d.get("log",[]) if x.get("date")!=date]+[{"date":date,"verified":{"reels_played":6},"actions":{"scrolls":5}}];json.dump(d,open(p,"w"));print('{"ok":true}')
PY
SH
cat >"$T/bin/sender" <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$1" >>"$MESSAGES"; echo MSGID=7001
SH
cat >"$T/bin/launchctl" <<'SH'
#!/usr/bin/env bash
echo "$*" >>"$KICKS"
SH
chmod +x "$T/bin/"*
new_case(){
  C="$T/$1"; mkdir -p "$C/home/.cloak" "$C/state"; echo '[]' >"$C/accounts"
  : >"$C/warm.calls"; : >"$C/messages"; : >"$C/kicks"
  export HOME="$C/home" CAPAFY_IG_ACCOUNTS_FILE="$C/accounts" CAPAFY_IG_LIFECYCLE_STATE="$C/state/lifecycle.json"
  export CAPAFY_OUTCOME_STATE_DIR="$C/state" CAPAFY_MARKETING_RESULT="$C/state/result.json"
  export CAPAFY_WARMUP_JITTER_MAX_SECONDS=0 CAPAFY_WARMUP_BROWSER="$T/bin/browser" CAPAFY_WARMUP_RUNNER="$T/bin/warm"
  export CAPAFY_TELEGRAM_SENDER="$T/bin/sender" CAPAFY_LAUNCHCTL="$T/bin/launchctl" CAPAFY_IG_LIFECYCLE="$LIFECYCLE"
  export WARM_CALLS="$C/warm.calls" MESSAGES="$C/messages" KICKS="$C/kicks"
  unset FAKE_WARM_MODE FAKE_DATE
}
active(){
  python3 - "$CAPAFY_IG_ACCOUNTS_FILE" <<'PY'
import json,sys
json.dump([{"handle":"capafy.skills25042","status":"warming","session_owner":"browser","browser_identity":"instagram:capafy-provision","port":9555,"created":"2026-08-01"}],open(sys.argv[1],"w"))
PY
}
count(){ python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["warmup_successes"])' "$CAPAFY_IG_LIFECYCLE_STATE"; }
capability(){ python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["capability"])' "$CAPAFY_IG_LIFECYCLE_STATE"; }

new_case none
bash "$WARMUP" >/dev/null 2>&1
eq "no account does not warm" "$(wc -l <"$WARM_CALLS" | tr -d ' ')" 0
eq "no account requests replacement" "$(python3 -c 'import json,sys;print(str(json.load(open(sys.argv[1]))["replacement_requested"]).lower())' "$CAPAFY_IG_LIFECYCLE_STATE")" true
eq "no account wakes manager" "$(wc -l <"$KICKS" | tr -d ' ')" 1

new_case noevidence; active; export FAKE_WARM_MODE=noevidence
bash "$WARMUP" >/dev/null 2>&1; rc=$?
[ "$rc" -ne 0 ] && ok "no evidence fails" || bad "no evidence accepted"
eq "no evidence count zero" "$(count)" 0

new_case sequence; active; export FAKE_DATE=2026-08-01
bash "$WARMUP" >/dev/null 2>&1
eq "first success counted" "$(count)" 1
eq "first transition reported" "$(grep -Fc 'verified warmup progress' "$MESSAGES")" 1
export FAKE_WARM_MODE=skip
bash "$WARMUP" >/dev/null 2>&1
eq "same date stays one" "$(count)" 1
eq "same date stays silent" "$(grep -Fc 'verified warmup progress' "$MESSAGES")" 1
unset FAKE_WARM_MODE; export FAKE_DATE=2026-08-02
bash "$WARMUP" >/dev/null 2>&1
eq "second date counted" "$(count)" 2
eq "second date grants noncommercial" "$(capability)" noncommercial_post

new_case abort; active; export FAKE_WARM_MODE=abort
bash "$WARMUP" >/dev/null 2>&1; rc=$?
[ "$rc" -ne 0 ] && ok "abort is nonzero" || bad "abort accepted"
eq "abort retires account" "$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))[0]["status"])' "$CAPAFY_IG_ACCOUNTS_FILE")" session_failed
eq "abort wakes manager" "$(wc -l <"$KICKS" | tr -d ' ')" 1

new_case seven; active
python3 - "$HOME/.cloak/ig-warmup-capafy.skills25042.json" <<'PY'
import json,sys
json.dump({"log":[{"date":f"2026-08-{d:02d}","verified":{"reels_played":6},"actions":{"scrolls":5}} for d in range(1,7)]},open(sys.argv[1],"w"))
PY
export FAKE_DATE=2026-08-07
bash "$WARMUP" >/dev/null 2>&1
eq "seven without reach stays noncommercial" "$(capability)" noncommercial_post
echo "=== test_capafy_ig_warmup: $P passed $F failed ==="
[ "$F" -eq 0 ]
