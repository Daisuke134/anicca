#!/usr/bin/env bash
# test-self-heal-tier0.sh — REAL fault-injection test for TIER 0 (self-heal spec
# 2026-07-01-openclaw-self-heal-design.md §4). No mocks (HARD RULE 0.24): injects a
# genuinely broken plugin entry into the REAL ~/.openclaw/openclaw.json (backed up
# first, restored after) and observes watchdog.sh detect+repair+ledger it live.
#
# Covers: F1 repair + ledger schema, escalation cooldown suppression, L1 report-only
# mode (config left untouched). F4 (gateway hang via SIGSTOP) was verified manually in
# the same session this test was written (real SIGSTOP + 2 consecutive watchdog.sh
# runs, consensus=2, real restart, ledger line, gateway responsive after) — not
# scripted here because it needs a live gateway PID to freeze and takes ~40s+ per run;
# see the self-heal-ledger.jsonl entries with failure_class=F4_scheduler_dead for
# evidence of that manual run.
set -uo pipefail
ANICCA_HOME="${ANICCA_HOME:-$HOME/.openclaw}"
CFG="$ANICCA_HOME/openclaw.json"
LEDGER="$ANICCA_HOME/state/self-heal-ledger.jsonl"
WATCHDOG="$ANICCA_HOME/skills/anicca-core/scripts/watchdog.sh"
MODE_FILE="$ANICCA_HOME/state/self-heal-mode.json"
COOLDOWN_FILE="$ANICCA_HOME/state/escalation-cooldown/F1_config_invalid.last"

PASS=0; FAIL=0
check() {
  if [ "$1" -eq 0 ]; then echo "PASS: $2"; PASS=$((PASS+1));
  else echo "FAIL: $2"; FAIL=$((FAIL+1)); fi
}
last_ledger_line_for() {
  grep "\"failure_class\": \"$1\"" "$LEDGER" 2>/dev/null | tail -1
}
inject_bad_plugin() {
  local ext="$ANICCA_HOME/extensions/tier0test"
  mkdir -p "$ext"
  cat > "$ext/package.json" <<'JSON'
{"name":"tier0test","openclaw":{"extensions":["./dist/index.js"]}}
JSON
  python3 - "$CFG" <<'PY'
import json,sys
cfg=sys.argv[1]
d=json.load(open(cfg))
d.setdefault("plugins",{}).setdefault("entries",{})["tier0test"]={"enabled":True}
json.dump(d,open(cfg,"w"),indent=2,ensure_ascii=False)
PY
}
cleanup_bad_plugin() {
  rm -rf "$ANICCA_HOME/extensions/tier0test"
  rm -rf "$ANICCA_HOME/.disabled-extensions"/tier0test-* 2>/dev/null
}

# snapshot state this test is about to mutate, so it can be restored byte-for-byte
# regardless of pass/fail (adversary finding: a prior version of this test left the
# escalation-cooldown file mutated, which could suppress a REAL future F1 alert for
# up to 24h — that must never survive a test run).
BAK="$CFG.test-bak-$(date +%s)"
cp "$CFG" "$BAK"
MODE_BAK=""
[ -f "$MODE_FILE" ] && MODE_BAK=$(cat "$MODE_FILE")
COOLDOWN_BAK=""
[ -f "$COOLDOWN_FILE" ] && COOLDOWN_BAK=$(cat "$COOLDOWN_FILE")
restore_all() {
  cleanup_bad_plugin
  cp "$BAK" "$CFG"; rm -f "$BAK"
  if [ -n "$MODE_BAK" ]; then printf '%s' "$MODE_BAK" > "$MODE_FILE"; fi
  mkdir -p "$(dirname "$COOLDOWN_FILE")"
  if [ -n "$COOLDOWN_BAK" ]; then printf '%s' "$COOLDOWN_BAK" > "$COOLDOWN_FILE"; else rm -f "$COOLDOWN_FILE"; fi
}
trap restore_all EXIT

echo "=== TEST 1: F1 config invalid -> real detect+repair+ledger (spec §4) ==="
# clear the cooldown for THIS test only (restore_all puts back whatever was really
# there, snapshotted above as COOLDOWN_BAK) so "first-time escalates" is actually
# testing the first-time case, not whatever cooldown state pre-existed this run.
rm -f "$COOLDOWN_FILE"
inject_bad_plugin
timeout 25 openclaw config validate >/tmp/tier0-validate-before.out 2>&1
grep -q "Config valid" /tmp/tier0-validate-before.out
check $((1-$?)) "config genuinely invalid after injection (precondition)"

LINES_BEFORE=$(wc -l < "$LEDGER" 2>/dev/null | tr -d ' ' || echo 0); LINES_BEFORE=${LINES_BEFORE:-0}
bash "$WATCHDOG" >/tmp/tier0-test-run.out 2>&1
timeout 25 openclaw config validate 2>&1 | grep -q "Config valid"
check $? "watchdog repaired config back to Config valid"

LINES_AFTER=$(wc -l < "$LEDGER" 2>/dev/null | tr -d ' ' || echo 0); LINES_AFTER=${LINES_AFTER:-0}
[ "$LINES_AFTER" -gt "$LINES_BEFORE" ]
check $? "self-heal-ledger.jsonl got a new line ($LINES_BEFORE -> $LINES_AFTER)"

last_ledger_line_for F1_config_invalid > /tmp/tier0-ledger-line.json
python3 - /tmp/tier0-ledger-line.json <<'PY'
import json,sys
try:
    line=open(sys.argv[1]).read().strip()
    d=json.loads(line)
    need = {"ts","failure_class","probe_output","action_taken","verify_result","tier","escalated"}
    missing = need - set(d.keys())
    sys.exit(1 if missing else 0)
except Exception:
    sys.exit(1)
PY
check $? "ledger line has full spec schema (ts/failure_class/probe_output/action_taken/verify_result/tier/escalated)"

grep -q '"escalated": true' /tmp/tier0-ledger-line.json
check $? "first-time F1 event has escalated=true (should_escalate had no prior cooldown entry)"

echo
echo "=== TEST 2: escalation cooldown suppresses an immediate repeat (spec §5 P3, task ask #4) ==="
inject_bad_plugin
bash "$WATCHDOG" >/tmp/tier0-test-run2.out 2>&1
timeout 25 openclaw config validate 2>&1 | grep -q "Config valid"
check $? "watchdog repaired the SECOND injection too (remediation is independent of escalation cooldown)"
last_ledger_line_for F1_config_invalid > /tmp/tier0-ledger-line2.json
grep -q '"escalated": false' /tmp/tier0-ledger-line2.json
check $? "second F1 event within cooldown window has escalated=false (no Telegram flood)"

echo
echo "=== TEST 3: L1 report-only mode does NOT mutate config (spec §5 rollout gate) ==="
printf '{"mode":"L1","note":"test"}\n' > "$MODE_FILE"
inject_bad_plugin
bash "$WATCHDOG" >/tmp/tier0-test-run3.out 2>&1
timeout 25 openclaw config validate 2>&1 | grep -q "Config valid"
check $((1-$?)) "L1 mode left config INVALID (no auto-repair happened, as designed)"
last_ledger_line_for F1_config_invalid > /tmp/tier0-ledger-line3.json
grep -q '"verify_result": "still_invalid"' /tmp/tier0-ledger-line3.json
check $? "L1 ledger entry correctly records still_invalid, not config_valid"
grep -q '"action_taken": "none (L1 report-only mode)"' /tmp/tier0-ledger-line3.json
check $? "L1 ledger entry correctly records no action was taken"
# restore to L2 and let the REAL repair run before final cleanup, proving the system
# is left healthy regardless of which mode branch ran last.
if [ -n "$MODE_BAK" ]; then printf '%s' "$MODE_BAK" > "$MODE_FILE"; else rm -f "$MODE_FILE"; fi
bash "$WATCHDOG" >/tmp/tier0-test-run4.out 2>&1
timeout 25 openclaw config validate 2>&1 | grep -q "Config valid"
check $? "after restoring L2, watchdog repaired the config left invalid by the L1 test"

restore_all
trap - EXIT
timeout 25 openclaw config validate 2>&1 | grep -q "Config valid"
check $? "real production config restored to valid after full test suite"
[ ! -f "$COOLDOWN_FILE" ] || [ "$(cat "$COOLDOWN_FILE")" = "$COOLDOWN_BAK" ]
check $? "escalation-cooldown state restored to pre-test value (no lingering suppression of a real future alert)"

echo
echo "=== RESULT: $PASS pass, $FAIL fail ==="
[ "$FAIL" -eq 0 ]
