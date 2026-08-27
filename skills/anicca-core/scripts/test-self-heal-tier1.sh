#!/usr/bin/env bash
# test-self-heal-tier1.sh — REAL fault-injection + real-incident-fix test for TIER 1
# (spec 2026-07-01-openclaw-self-heal-design.md §4). No mocks (HARD RULE 0.24).
#
# F2 (dependency missing) and F5 (log bloat) were verified against a GENUINE,
# already-broken production incident found live 2026-07-04 (NOT synthetic fault
# injection): ai.anicca.agentmail-webhook and ai.openclaw.anicca-ask were both
# crash-looping on "Cannot find package 'express'" (agentmail-webhook alone had logged
# 61,095 repeats into a 21MB err log — the exact incident shape this spec cites). This
# test asserts the ledger evidence tier1-remediate.sh already wrote for that real fix
# rather than re-injecting the same fault synthetically (npm install against a
# currently-healthy service would just be a no-op and prove nothing new).
#
# F3 (binary missing) IS injected synthetically here, via a throwaway, fully
# self-contained launchd job + fake err log (never touches any real production
# service) — installs/uninstalls GNU `hello` (a tiny, harmless, verifiably-absent-
# by-default brew formula) and cleans up completely regardless of pass/fail.
set -uo pipefail
ANICCA_HOME="${ANICCA_HOME:-$HOME/.openclaw}"
LEDGER="$ANICCA_HOME/state/self-heal-ledger.jsonl"
TIER1="$ANICCA_HOME/skills/anicca-core/scripts/tier1-remediate.sh"

PASS=0; FAIL=0
check() {
  if [ "$1" -eq 0 ]; then echo "PASS: $2"; PASS=$((PASS+1));
  else echo "FAIL: $2"; FAIL=$((FAIL+1)); fi
}

echo "=== TEST 1: F2 (dep-missing) real-incident evidence (agentmail-webhook + anicca-ask) ==="
# Single grep, no pipe: under `set -o pipefail`, `grep X | grep -q Y` turns into a
# LATENT failure once the file grows — grep -q exits at the first match and the
# still-writing left grep dies with SIGPIPE (141), failing the pipeline even though
# the evidence line exists (surfaced 2026-07-27 when the ledger passed ~750KB).
grep -q '"failure_class": "F2_dep_missing".*ai.anicca.agentmail-webhook.*"verify_result": "verified_clean"' "$LEDGER"
check $? "ledger has a verified_clean F2 fix for ai.anicca.agentmail-webhook"
grep -q '"failure_class": "F2_dep_missing".*ai.openclaw.anicca-ask.*"verify_result": "verified_clean"' "$LEDGER"
check $? "ledger has a verified_clean F2 fix for ai.openclaw.anicca-ask"
ls "/Users/anicca/anicca-oss/.worktrees/agentmail/runtime/agentmail/node_modules/express" >/dev/null 2>&1
check $? "express is genuinely installed in agentmail-webhook's WorkingDirectory (real side effect, not a log claim)"
curl -s -o /dev/null --max-time 5 http://127.0.0.1:8810/
check $? "agentmail-webhook is genuinely listening on :8810 right now (real process, not a ledger claim)"

echo
echo "=== TEST 2: F5 (log bloat) real truncation of the 21MB agentmail-webhook.err.log ==="
grep -q '"failure_class": "F5_disk_log_bloat".*agentmail-webhook.*"verify_result": "truncated_to_0mb"' "$LEDGER"
check $? "ledger has the F5 truncation event for agentmail-webhook.err.log"
ARCHIVE=$(ls "$ANICCA_HOME"/state/self-heal-log-archive/agentmail-webhook.err.log.*.tail.gz 2>/dev/null | tail -1)
[ -n "$ARCHIVE" ] && gunzip -t "$ARCHIVE" 2>/dev/null
check $? "the archived tail is a real, valid gzip (not a fabricated ledger claim)"
LINES=$(gunzip -c "$ARCHIVE" 2>/dev/null | wc -l | tr -d ' ')
[ "${LINES:-0}" -eq 2000 ]
check $? "archive contains exactly the expected 2000 lines"
CURRENT_SIZE=$(stat -f %z "$ANICCA_HOME/logs/agentmail-webhook.err.log" 2>/dev/null || echo 999999999)
[ "$CURRENT_SIZE" -lt 1048576 ]
check $? "the live err log is genuinely small now (< 1MB), not just claimed truncated"

echo
echo "=== TEST 3: F3 (binary-missing) — real, bounded, throwaway-job fault injection ==="
TESTDIR=$(mktemp -d /tmp/tier1-f3-test.XXXXXX)
PLIST="$HOME/Library/LaunchAgents/ai.anicca.tier1-f3-throwaway-test.plist"
cleanup_f3() {
  launchctl unload "$PLIST" >/dev/null 2>&1 || true
  rm -f "$PLIST"
  rm -rf "$TESTDIR"
  brew uninstall hello >/dev/null 2>&1 || true
}
trap cleanup_f3 EXIT

command -v hello >/dev/null 2>&1
check $((1-$?)) "'hello' genuinely absent before the test (precondition)"

cat > "$TESTDIR/test.err.log" <<'EOF'
some prior harmless log line
sh: hello: command not found
EOF
cat > "$PLIST" <<PLISTXML
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>ai.anicca.tier1-f3-throwaway-test</string>
  <key>ProgramArguments</key>
  <array><string>/bin/sh</string><string>-c</string><string>sleep 3600</string></array>
  <key>WorkingDirectory</key><string>$TESTDIR</string>
  <key>StandardErrorPath</key><string>$TESTDIR/test.err.log</string>
  <key>RunAtLoad</key><false/>
</dict>
</plist>
PLISTXML
launchctl load "$PLIST" >/dev/null 2>&1

LINES_BEFORE=$(wc -l < "$LEDGER" 2>/dev/null | tr -d ' '); LINES_BEFORE=${LINES_BEFORE:-0}
# Clear the cooldown for ONLY this test's own throwaway key so the test is re-runnable —
# a real bug was found and fixed here: a first version of this test set
# SELF_HEAL_REMEDIATION_COOLDOWN_S=0 globally for the whole tier1-remediate.sh run, which
# also bypassed the REAL production services' (anicca-ask, agentmail-webhook,
# phone-conversation) remediation cooldowns, causing several unnecessary extra
# npm-install+restart cycles against real running services just to re-run this F3 test.
# Never do that again — only ever clear the cooldown file for the throwaway key.
rm -f "$ANICCA_HOME/state/remediation-cooldown/F3_ai.anicca.tier1-f3-throwaway-test_hello.last"
bash "$TIER1" >/tmp/tier1-f3-test-run.out 2>&1
LINES_AFTER=$(wc -l < "$LEDGER" 2>/dev/null | tr -d ' '); LINES_AFTER=${LINES_AFTER:-0}
[ "$LINES_AFTER" -gt "$LINES_BEFORE" ]
check $? "ledger got a new line for the F3 injection"

command -v hello >/dev/null 2>&1
check $? "'hello' is genuinely installed now (real brew install, not a log claim)"

# search for OUR throwaway job's entry by label, not by ledger position — F5 (correctly,
# post-fix) may append further real entries for OTHER jobs after this run too (found
# live: F5 now genuinely sees anicca-ask's real log path and truncated it in the same
# run, which used to be structurally invisible to F5 before the FIND-1 fix — that's a
# feature, not a test bug, so the test must not assume "last line" positionally).
THROWAWAY_LINE=$(grep 'tier1-f3-throwaway-test' "$LEDGER" | tail -1)
printf '%s' "$THROWAWAY_LINE" | grep -q '"failure_class": "F3_binary_missing"'
check $? "our throwaway job's ledger entry is F3_binary_missing"
printf '%s' "$THROWAWAY_LINE" | grep -q '"verify_result": "verified_present"'
check $? "our throwaway job's ledger entry correctly records verified_present"

cleanup_f3
trap - EXIT
command -v hello >/dev/null 2>&1
check $((1-$?)) "'hello' genuinely uninstalled again — no residue left on the system"
[ ! -f "$PLIST" ]
check $? "throwaway plist file removed — no residue left on the system"

echo
echo "=== TEST 4: per-instance escalation key — two jobs sharing a failure_class each escalate independently ==="
# adversary finding 2026-07-04: record_action() used to key should_escalate() by the bare
# failure_class string ("F2_dep_missing"), shared across EVERY job. Confirmed live: job A's
# escalation silently consumed the 24h cooldown token for job B's completely different,
# still-unresolved incident (5 consecutive real phone-conversation alerts suppressed by an
# unrelated agentmail-webhook alert). Isolated unit test (no real service touched) proving
# the fix: two DIFFERENT escalation_key values for the same failure_class each escalate.
# ISO_HOME isolates only the STATE (cooldown files etc.) — the lib SCRIPT ITSELF is
# still the real, production skills/_shared/scripts/self-heal-lib.sh (passed explicitly
# as $1), so this genuinely exercises the shipped code, not a copy.
REAL_LIB="$ANICCA_HOME/skills/_shared/scripts/self-heal-lib.sh"
ISO_HOME=$(mktemp -d /tmp/tier1-esc-test.XXXXXX)
RESULT=$(ANICCA_HOME="$ISO_HOME" NOW=$(date +%s) TIER=1 bash -c '
  . "$1"
  record_action "F2_dep_missing" "msg-A" "po-A" "at-A" "vr-A" "F2_dep_missing_jobA"
  A_ESCALATED=$([ -n "$ESCALATE_ACTIONS" ] && echo yes || echo no)
  ESCALATE_ACTIONS=""
  record_action "F2_dep_missing" "msg-B" "po-B" "at-B" "vr-B" "F2_dep_missing_jobB"
  B_ESCALATED=$([ -n "$ESCALATE_ACTIONS" ] && echo yes || echo no)
  echo "A=$A_ESCALATED B=$B_ESCALATED"
' _ "$REAL_LIB")
echo "$RESULT" | grep -q "A=yes B=yes"
check $? "two different jobs sharing the SAME failure_class both escalate independently (was: B suppressed by A)"
rm -rf "$ISO_HOME"

echo
echo "=== TEST 5: should_remediate() 1h cooldown genuinely blocks a same-window retry (spec §3.1 P3) ==="
# adversary finding 2026-07-04: the ONE mechanism meant to satisfy "bounded loops" for a
# repeatedly-failing fix (should_remediate's cooldown) had ZERO test coverage — a broken
# fix could otherwise be re-attempted every 15-min cycle forever. Isolated (no real
# service touched): call should_remediate() twice for the same key inside the cooldown
# window, then again after the window elapses.
ISO_HOME2=$(mktemp -d /tmp/tier1-remcooldown-test.XXXXXX)
RESULT2=$(ANICCA_HOME="$ISO_HOME2" NOW=$(date +%s) TIER=1 SELF_HEAL_REMEDIATION_COOLDOWN_S=3 bash -c '
  . "$1"
  should_remediate "test_job_key" && echo -n "call1=yes " || echo -n "call1=no "
  should_remediate "test_job_key" && echo -n "call2=yes " || echo -n "call2=no "
  sleep 4
  NOW=$(date +%s)
  should_remediate "test_job_key" && echo "call3=yes" || echo "call3=no"
' _ "$REAL_LIB")
echo "$RESULT2" | grep -q "call1=yes call2=no call3=yes"
check $? "cooldown blocks an immediate 2nd attempt (call2=no) and allows a 3rd after the window elapses (call3=yes): got [$RESULT2]"
rm -rf "$ISO_HOME2"

echo
echo "=== RESULT: $PASS pass, $FAIL fail ==="
[ "$FAIL" -eq 0 ]
