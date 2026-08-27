#!/usr/bin/env bash
# test-self-heal-f7-silence.sh — F7: a loop that exits 0 and produces nothing.
#
# Every existing failure class is a CRASH class: F2 missing dependency, F3 missing
# binary, F5 log bloat, F6 provider outage. All of them need the process to die. But
# the way loops actually died here was quieter: gig ran for 4.5 days exiting 0 with a
# green test suite while its ledgers stood still; larry, capafy and clipping all show
# "Status 0" in launchctl right now. openclaw cron cannot see this either -- its docs
# say "Exit code 0 records the run ok" and a NO_REPLY is suppressed by design.
#
# F7 therefore judges a loop by its OUTPUT, not by its exit code: each loop declares
# the ledger that grows when it does real work, and how long silence is allowed.
#
# No mocks (HARD RULE 0.24): real files with real mtimes, in an isolated ANICCA_HOME
# so no production ledger or cooldown is touched.
set -uo pipefail
CHECKER="${ANICCA_HOME:-$HOME/.openclaw}/skills/anicca-core/scripts/f7-silence-check.sh"

PASS=0; FAIL=0
check() {
  if [ "$1" -eq 0 ]; then echo "PASS: $2"; PASS=$((PASS+1));
  else echo "FAIL: $2  (expected=$3 got=$4)"; FAIL=$((FAIL+1)); fi
}

WORK=$(mktemp -d /tmp/f7-silence.XXXXXX)
trap 'rm -rf "$WORK"' EXIT
ISO="$WORK/home"; mkdir -p "$ISO/state"
LEDGER_JSON="$ISO/state/self-heal-ledger.jsonl"

FRESH="$WORK/fresh.jsonl"; printf '{"a":1}\n' > "$FRESH"
STALE="$WORK/stale.jsonl"; printf '{"a":1}\n' > "$STALE"; touch -t 202607200000 "$STALE"
GONE="$WORK/missing.jsonl"

MANIFEST="$WORK/manifest.json"
cat > "$MANIFEST" <<EOF
{"loops":[
 {"label":"loop-healthy","max_silence_hours":24,"ledgers":["$FRESH"]},
 {"label":"loop-silent","max_silence_hours":6,"ledgers":["$STALE"]},
 {"label":"loop-any-of-two","max_silence_hours":24,"ledgers":["$STALE","$FRESH"]},
 {"label":"loop-no-ledger","max_silence_hours":6,"ledgers":["$GONE"]}
]}
EOF

echo "=== F7 checker exists and runs ==="
[ -x "$CHECKER" ] || [ -f "$CHECKER" ]
check $? "f7-silence-check.sh exists" "present" "absent"

OUT=$(ANICCA_HOME="$ISO" F7_MANIFEST="$MANIFEST" bash "$CHECKER" 2>"$WORK/err")
RC=$?
check $((RC==0?0:1)) "checker exits 0" 0 "$RC"

echo
echo "=== a silent loop is reported, a productive one is not ==="
grep -q '"failure_class": "F7_silent_barren"' "$LEDGER_JSON" 2>/dev/null
check $? "ledger got an F7 entry" "F7 entry" "none"

grep -q 'loop-silent' "$LEDGER_JSON" 2>/dev/null
check $? "the silent loop is named" "loop-silent" "missing"

if grep -q 'loop-healthy' "$LEDGER_JSON" 2>/dev/null; then healthy=named; else healthy=absent; fi
[ "$healthy" = "absent" ]
check $? "a loop whose ledger is fresh is NOT reported" "absent" "$healthy"

# Freshness is per-loop, not per-file: one live ledger means the loop is working.
if grep -q 'loop-any-of-two' "$LEDGER_JSON" 2>/dev/null; then anyof=named; else anyof=absent; fi
[ "$anyof" = "absent" ]
check $? "any one fresh ledger clears the loop" "absent" "$anyof"

echo
echo "=== a declared ledger that does not exist is a finding, not a crash ==="
grep -q 'loop-no-ledger' "$LEDGER_JSON" 2>/dev/null
check $? "a missing ledger is reported" "reported" "missing"
[ ! -s "$WORK/err" ]
check $? "checker wrote nothing to stderr" "empty" "$(head -c 80 "$WORK/err" 2>/dev/null)"

echo
echo "=== silence is measured, not asserted ==="
grep 'loop-silent' "$LEDGER_JSON" 2>/dev/null | grep -qE 'silent_hours=[0-9]+'
check $? "the entry carries the measured silence in hours" "silent_hours=N" "absent"

echo
echo "=== the real production manifest is valid and points at real ledgers ==="
REAL="${ANICCA_HOME:-$HOME/.openclaw}/state/f7-loop-manifest.json"
[ -f "$REAL" ]
check $? "production manifest exists" "present" "absent"
python3 -c "
import json,sys,os
m=json.load(open(sys.argv[1]))
loops=m['loops']
assert loops, 'no loops declared'
for l in loops:
    assert l['label'] and l['ledgers'] and l['max_silence_hours'] > 0, l
    # at least one declared ledger must exist on this machine, or the declaration is fiction
    assert any(os.path.exists(os.path.expanduser(p)) for p in l['ledgers']), l['label']
print(len(loops))
" "$REAL" >/dev/null 2>&1
check $? "every declared loop names at least one ledger that exists" "valid" "invalid"

echo
echo "RESULT: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
