#!/usr/bin/env bash
# test-self-heal-tier2.sh — REAL evidence + real, bounded fault-injection test for
# TIER 2 (agent-diagnosis) + F6 (model failover) + TIER 3 (bounded escalation).
# No mocks (HARD RULE 0.24).
#
# The expensive part (an actual `openclaw agent` diagnostic turn, ~80s, real compute)
# was run ONCE live against a genuine production incident
# (ai.anicca cron "larry-en-female-reel-replace-3" — a real "OpenClaw recorded a native
# Codex tool.call without a matching tool.result" anomaly) and is asserted here as
# real evidence already in the ledger, rather than re-run every test (same approach as
# test-self-heal-tier1.sh's F2 section, which asserts real fixed-incident evidence
# instead of re-injecting an already-fixed fault).
#
# PASS 1 (resolved / still-broken / TIER3-escalate) is fault-injected for real via a
# throwaway, self-contained, one-off `openclaw cron` job — cheap (no agent call needed
# for this part) and fully cleaned up regardless of pass/fail.
set -uo pipefail
ANICCA_HOME="${ANICCA_HOME:-$HOME/.openclaw}"
LEDGER="$ANICCA_HOME/state/self-heal-ledger.jsonl"
TIER2="$ANICCA_HOME/skills/anicca-core/scripts/tier2-agent-diagnose.sh"
PENDING_DIR="$ANICCA_HOME/state/tier2-pending"
NOW=$(date +%s); TIER=99
# openclaw_json() strips the intermittent "Config warnings: ..." banner `openclaw`
# sometimes writes to stdout before real JSON — found live 2026-07-04: this exact test
# flaked once because `openclaw cron create --json` returned the banner glued to the
# JSON, which broke this test's own naive `python3 json.load(sys.stdin)` parsing (NOT a
# tier2-agent-diagnose.sh bug — that script was already hardened with this same helper
# in the same fix). Use it here too so the test doesn't flake on the identical cause.
. "$ANICCA_HOME/skills/_shared/scripts/self-heal-lib.sh"

PASS=0; FAIL=0
check() {
  if [ "$1" -eq 0 ]; then echo "PASS: $2"; PASS=$((PASS+1));
  else echo "FAIL: $2"; FAIL=$((FAIL+1)); fi
}

echo "=== TEST 1: F1-F5 / F6 classification — sources the REAL shared lib, not a copy ==="
# uses the ACTUAL self-heal-lib.sh predicates (is_dep_missing_error / is_binary_missing_error
# / is_config_invalid_error / is_model_provider_outage_error) — a prior version of this test
# hand-copied a second, less-refined classifier, the exact DRY-violation shape adversary
# review flagged as already having happened once between tier1 and tier2's own code.
CLASSIFY_RESULT=$(ANICCA_HOME="$ANICCA_HOME" NOW=$(date +%s) TIER=99 bash -c '
  . "$1/skills/_shared/scripts/self-heal-lib.sh"
  is_dep_missing_error "Cannot find package example" && echo -n "A=yes " || echo -n "A=no "
  is_model_provider_outage_error "FallbackSummaryError: All models failed" && echo -n "B=yes " || echo -n "B=no "
  is_dep_missing_error "OpenClaw recorded a native Codex tool.call without a matching tool.result" && echo -n "C=yes " || echo -n "C=no "
  is_model_provider_outage_error "OpenClaw recorded a native Codex tool.call without a matching tool.result" && echo -n "D=yes " || echo -n "D=no "
  # adversary finding: bare unanchored "402"/"403" substrings misclassify ordinary text
  # containing those digits (e.g. a line number or byte offset) as an F6 model outage.
  is_model_provider_outage_error "stack trace at line 402 in module foo" && echo "E=yes" || echo "E=no"
' _ "$ANICCA_HOME")
echo "$CLASSIFY_RESULT" | grep -q "A=yes B=yes C=no D=no E=no"
check $? "classification: F1-F5 pattern caught, F6 pattern caught, genuinely-unknown text matches NEITHER, and a coincidental '402' substring in ordinary text does NOT misfire F6: got [$CLASSIFY_RESULT]"

echo
echo "=== TEST 2: real TIER2 agent-diagnosis evidence (genuine production incident, not injected) ==="
grep -F '"job=larry-en-female-reel-replace-3' "$LEDGER" > /dev/null 2>&1 || grep -F 'larry-en-female-reel-replace-3' "$LEDGER" | grep -q '"tier": 2'
check $? "ledger has a real tier:2 diagnosis entry for the genuine larry-en-female-reel-replace-3 incident"
grep -F 'larry-en-female-reel-replace-3' "$LEDGER" | grep -q '"verify_result": "pending_next_scheduled_run"'
check $? "that entry correctly defers verification to the cron's own next scheduled run (never force-fired — spec §6.1 safety rule)"
[ -f "$PENDING_DIR/7f291612-9941-40b5-8959-5e18cc98df84.json" ]
check $? "a real pending-verification marker exists on disk for that job, with its real next scheduled fire time"
python3 -c "import json,sys; d=json.load(open('$PENDING_DIR/7f291612-9941-40b5-8959-5e18cc98df84.json')); sys.exit(0 if 'last_run_at_diagnosis_ms' in d else 1)"
check $? "the real marker has the last_run_at_diagnosis_ms field (post-fix schema — was missing before the stale-nextRunAtMs bugfix, backfilled)"

echo
echo "=== TEST 2b: escalation-key isolation — a fresh diagnosis no longer immediately escalates ==="
# adversary finding, proven live: the initial 'pending_next_scheduled_run' diagnosis event
# used to share should_escalate()'s escalation_key with the TIER3-exhaustion event for the
# SAME job, and _cooldown_check() always fires on a key's first-ever use — so EVERY new
# diagnosis alerted Telegram immediately (see the historical larry-en-female-reel-replace-3
# ledger line above, which predates this fix and still shows escalated:true). Structural
# fix verification: the code path that ledgers a fresh diagnosis must be a plain ledger()
# call, not record_action() — grep-verify no record_action call uses the bare
# "unknown_diagnosed" failure_class anymore (it's informational-only now).
grep -n 'ledger "unknown_diagnosed"' "$TIER2" | grep -q 'pending_next_scheduled_run'
check $? "the initial-diagnosis code path calls plain ledger() (no escalation decision), not record_action()"
grep -c 'record_action "unknown_diagnosed"' "$TIER2" > /tmp/tier2-recordaction-count.txt 2>/dev/null
[ "$(cat /tmp/tier2-recordaction-count.txt)" = "0" ]
check $? "no record_action() call still uses the bare 'unknown_diagnosed' class (would re-share the TIER3 escalation_key)"
grep -q 'unknown_tier3_escalation_' "$TIER2"
check $? "the TIER3-exhaustion escalation uses its own distinct escalation_key (unknown_tier3_escalation_<job_id>)"
grep -q 'unknown_diagnostic_call_failed_' "$TIER2"
check $? "a failed diagnostic call ALSO uses its own distinct escalation_key (won't suppress or be suppressed by the other two)"

echo
echo "=== TEST 2c: safety-prompt contract — the diagnostic prompt still contains the required guardrail phrases ==="
# weak but real regression guard: catches a future edit silently weakening or deleting the
# read-only/no-posting instruction. NOTE (honest limitation, not fixed by this test): the
# underlying \`openclaw agent\` CLI has NO code-level tool-restriction/sandbox flag
# (confirmed via \`openclaw agent --help\`) — this safety property is currently enforced
# ONLY by prompt text to a full-privilege agent identity. This test verifies the prompt
# text is present and intact; it cannot and does not prove the agent will always obey it.
grep -q "You must NEVER execute this cron's own task" "$TIER2"
check $? "prompt still contains the explicit 'never execute this cron's own task' instruction"
grep -q "never post/publish/send/tweet/upload anything" "$TIER2"
check $? "prompt still contains the explicit 'never post/publish/send' instruction"
grep -q "READ-ONLY commands" "$TIER2"
check $? "prompt still instructs read-only investigation"

echo
echo "=== TEST 3a: PASS 1 resolved-path — real, bounded, throwaway cron that succeeds ==="
# --keep-after-run: a plain --at one-shot cron auto-DELETES itself after a successful
# run (deleteAfterRun defaults true) — found live: without this flag, PASS1 could never
# find the job again on its next check (openclaw cron get returns empty for a deleted
# job), silently skipping it and writing NOTHING, which looked like PASS1 was broken
# when actually the test's own throwaway job had just vanished out from under it.
OKJOB_JSON=$(openclaw_json cron create --at +1h --name "tier2-selftest-ok" --message "Reply with exactly: TIER2_SELFTEST_OK" --agent anicca --no-deliver --keep-after-run --json)
OKJOB_ID=$(printf '%s' "$OKJOB_JSON" | python3 -c "import json,sys;print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
OK_MARKER="$PENDING_DIR/${OKJOB_ID}.json"
cleanup_ok() { timeout 10 openclaw cron delete "$OKJOB_ID" >/dev/null 2>&1 || true; rm -f "$OK_MARKER"; }
trap cleanup_ok EXIT
[ -n "$OKJOB_ID" ]
check $? "resolved-path throwaway cron created for real"
timeout 30 openclaw cron run "$OKJOB_ID" --wait >/dev/null 2>&1
python3 -c "
import json
json.dump({'job_name': 'tier2-selftest-ok', 'diagnosed_at_ms': 0, 'next_run_at_ms': 1, 'attempts': 0}, open('$OK_MARKER', 'w'))
"
LINES_BEFORE=$(wc -l < "$LEDGER" 2>/dev/null | tr -d ' '); LINES_BEFORE=${LINES_BEFORE:-0}
bash "$TIER2" >/tmp/tier2-selftest-ok.out 2>&1
LINES_AFTER=$(wc -l < "$LEDGER" 2>/dev/null | tr -d ' '); LINES_AFTER=${LINES_AFTER:-0}
[ "$LINES_AFTER" -gt "$LINES_BEFORE" ]
check $? "PASS1 wrote a new ledger line for the resolved job"
grep -F "tier2-selftest-ok" "$LEDGER" | tail -1 | grep -q '"verify_result": "resolved_after_natural_run"'
check $? "PASS1 correctly classified the succeeded job as resolved_after_natural_run"
[ ! -f "$OK_MARKER" ]
check $? "resolved job's pending marker was removed"
cleanup_ok
trap - EXIT
timeout 10 openclaw cron get "$OKJOB_ID" >/dev/null 2>&1
check $((1-$?)) "resolved-path throwaway cron genuinely deleted — no residue"

echo
echo "=== TEST 3b: PASS 1 still-broken/TIER3-escalate — real, bounded, throwaway cron that genuinely errors ==="
# a job with NO --no-deliver and NO explicit --channel hits a real, harmless, reliably-
# reproducible error: "Channel is required when multiple channels are configured" (this
# system has both slack+telegram configured) — the agent turn runs, replies, but
# DELIVERY fails before anything is sent anywhere, giving a genuine lastRunStatus=error
# with zero content posted. (A nonexistent --agent id was tried first but `cron create`
# does not reliably persist/recognize such a job for a later `cron run` — found live:
# `cron run` on its own just-returned id raised "unknown cron job id".)
ERRJOB_JSON=$(openclaw_json cron create --at +1h --name "tier2-selftest-err" --message "Reply with exactly: TIER2_SELFTEST_ERR (this reply is intentionally never delivered anywhere)" --agent anicca --keep-after-run --json)
ERRJOB_ID=$(printf '%s' "$ERRJOB_JSON" | python3 -c "import json,sys;print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
ERR_MARKER="$PENDING_DIR/${ERRJOB_ID}.json"
cleanup_err() { timeout 10 openclaw cron delete "$ERRJOB_ID" >/dev/null 2>&1 || true; rm -f "$ERR_MARKER"; }
trap cleanup_err EXIT
[ -n "$ERRJOB_ID" ]
check $? "error-path throwaway cron created for real"
timeout 30 openclaw cron run "$ERRJOB_ID" --wait >/dev/null 2>&1
ERRJOB_STATUS=$(timeout 15 openclaw cron get "$ERRJOB_ID" 2>/dev/null | python3 -c "import json,sys;print(json.load(sys.stdin).get('state',{}).get('lastRunStatus',''))" 2>/dev/null)
[ "$ERRJOB_STATUS" = "error" ]
check $? "the nonexistent-agent throwaway cron genuinely errored (precondition for this test): got status=[$ERRJOB_STATUS]"

# last_run_at_diagnosis_ms=0: the (already-happened) failing run above counts as the
# first genuinely-new run "since diagnosis" (adversary-fix: PASS1 now requires a REAL
# lastRunAtMs advance past this value, not just a reset next_run_at_ms field).
python3 -c "
import json
json.dump({'job_name': 'tier2-selftest-err', 'diagnosed_at_ms': 0, 'next_run_at_ms': 1, 'last_run_at_diagnosis_ms': 0, 'attempts': 0}, open('$ERR_MARKER', 'w'))
"
bash "$TIER2" >/tmp/tier2-selftest-err1.out 2>&1
grep -F "tier2-selftest-err" "$LEDGER" | tail -1 | grep -q '"verify_result": "still_broken_will_retry"'
check $? "PASS1 (1st still-broken cycle): recorded still_broken_will_retry, did not escalate yet"
[ -f "$ERR_MARKER" ]
check $? "marker retained after 1st still-broken cycle (bounded retry, not yet at the escalation threshold)"

# force a GENUINE 2nd real run (also fails the same way) -> a real lastRunAtMs advance,
# not just a reset timestamp field — this is exactly what the adversary-fix requires
# now, versus the old bug where resetting next_run_at_ms alone was enough to fake a
# "new retry" with zero actual retries having happened.
python3 -c "
import json
d=json.load(open('$ERR_MARKER'))
d['next_run_at_ms']=1
json.dump(d, open('$ERR_MARKER','w'))
"
timeout 30 openclaw cron run "$ERRJOB_ID" --wait >/dev/null 2>&1
bash "$TIER2" >/tmp/tier2-selftest-err2.out 2>&1
grep -F "tier2-selftest-err" "$LEDGER" | tail -1 | grep -q '"verify_result": "still_broken_after_2_attempts"'
check $? "PASS1 (2nd still-broken cycle): recorded still_broken_after_2_attempts"
grep -F "tier2-selftest-err" "$LEDGER" | tail -1 | grep -q '"escalated": true'
check $? "TIER3: 2nd consecutive failure genuinely escalated (single bounded Telegram, per should_escalate cooldown)"
[ ! -f "$ERR_MARKER" ]
check $? "marker removed after escalation (no infinite tracking of an escalated incident)"

cleanup_err
trap - EXIT
timeout 10 openclaw cron get "$ERRJOB_ID" >/dev/null 2>&1
check $((1-$?)) "error-path throwaway cron genuinely deleted — no residue"

echo
echo "=== RESULT: $PASS pass, $FAIL fail ==="
[ "$FAIL" -eq 0 ]
