#!/usr/bin/env bash
# VSDD oracle -- post-adversary FIND-006 fix: lib/note-fetch-views.py existed (PROP-28) but was never
# invoked on ANY cadence -- metrics would never actually collect unless someone ran it by hand. run.sh's
# new run_metrics_pass_on_exit (an EXIT trap, so it fires regardless of which of run.sh's many `exit 0`
# branches this wake takes) now wires it in, opt-in via ARTICLE_METRICS_PASS=1 (default OFF so an ad-hoc/
# test invocation never makes an unexpected network call).
set -uo pipefail
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

CALL_LOG_DIR="$(mktemp -d)"
VIEWS_STUB="$CALL_LOG_DIR/stub-fetch-views.sh"
cat > "$VIEWS_STUB" << 'SHEOF'
#!/usr/bin/env bash
echo "called" >> "$VIEWS_STUB_CALL_LOG"
echo '{"summary": true, "processed": 0, "views_recorded": 0, "views_none": 0}'
exit 0
SHEOF
chmod +x "$VIEWS_STUB"

# ---------- default (ARTICLE_METRICS_PASS unset): the metrics pass is NEVER invoked ----------
T1="$(mktemp -d)"
CALL_LOG1="$CALL_LOG_DIR/calls-1.log"; : > "$CALL_LOG1"
OUT1="$(VIEWS_STUB_CALL_LOG="$CALL_LOG1" ARTICLE_NOTE_FETCH_VIEWS_PY="$VIEWS_STUB" \
  ARTICLE_TEST=1 ARTICLE_DIR="$T1" AUTONOMY=off ARTICLE_TEST_TOPIC="AI agents" ARTICLE_TEST_RESEARCH=sufficient \
  ARTICLE_TEST_V0_RESULTS="PASS" ARTICLE_TEST_V05_RESULTS="PASS" bash "$SKILL/run.sh" 2>&1)"; rc1=$?
ok "$([ $rc1 -eq 0 ] && echo 1 || echo 0)" "wake completes, rc=0 (rc=$rc1): $OUT1"
ok "$([ ! -s "$CALL_LOG1" ] && echo 1 || echo 0)" "default (ARTICLE_METRICS_PASS unset): the metrics pass is NEVER invoked (call log: $(cat "$CALL_LOG1" 2>/dev/null))"

# ---------- ARTICLE_METRICS_PASS=1: the metrics pass IS invoked, even on a SKIPPED wake (no viable topic) --
# proving it runs independent of what THIS wake itself did, not just on a successful publish ----------
T2="$(mktemp -d)"
CALL_LOG2="$CALL_LOG_DIR/calls-2.log"; : > "$CALL_LOG2"
OUT2="$(VIEWS_STUB_CALL_LOG="$CALL_LOG2" ARTICLE_NOTE_FETCH_VIEWS_PY="$VIEWS_STUB" ARTICLE_METRICS_PASS=1 \
  ARTICLE_TEST=1 ARTICLE_DIR="$T2" AUTONOMY=off ARTICLE_TEST_TOPIC="" ARTICLE_TEST_RESEARCH=insufficient \
  bash "$SKILL/run.sh" 2>&1)"; rc2=$?
ok "$([ $rc2 -eq 0 ] && echo 1 || echo 0)" "wake completes, rc=0 (rc=$rc2): $OUT2"
ok "$(grep -q 'last_wake_result: SKIPPED' "$T2/STATE.md" 2>/dev/null && echo 1 || echo 0)" "this wake SKIPPED (no viable topic) -- sanity check the scenario is what it claims"
ok "$(grep -c 'called' "$CALL_LOG2" 2>/dev/null | grep -q '^1$' && echo 1 || echo 0)" "ARTICLE_METRICS_PASS=1: the metrics pass IS invoked EXACTLY ONCE, even on a SKIPPED wake (independent of this wake's own publish outcome): $(cat "$CALL_LOG2" 2>/dev/null)"

# ---------- ARTICLE_METRICS_PASS=1 on an ABORTED wake: still invoked exactly once ----------
T3="$(mktemp -d)"
CALL_LOG3="$CALL_LOG_DIR/calls-3.log"; : > "$CALL_LOG3"
OUT3="$(VIEWS_STUB_CALL_LOG="$CALL_LOG3" ARTICLE_NOTE_FETCH_VIEWS_PY="$VIEWS_STUB" ARTICLE_METRICS_PASS=1 \
  ARTICLE_TEST=1 ARTICLE_DIR="$T3" AUTONOMY=off ARTICLE_TEST_TOPIC="AI agents" ARTICLE_TEST_RESEARCH=sufficient \
  ARTICLE_TEST_V0_RESULTS="FAIL,FAIL,FAIL" ARTICLE_TEST_V05_RESULTS="FAIL,FAIL,FAIL" bash "$SKILL/run.sh" 2>&1)"; rc3=$?
ok "$([ $rc3 -eq 0 ] && echo 1 || echo 0)" "wake completes, rc=0 (rc=$rc3): $OUT3"
ok "$(grep -q 'last_wake_result: ABORTED' "$T3/STATE.md" 2>/dev/null && echo 1 || echo 0)" "this wake ABORTED -- sanity check the scenario is what it claims"
ok "$(grep -c 'called' "$CALL_LOG3" 2>/dev/null | grep -q '^1$' && echo 1 || echo 0)" "ARTICLE_METRICS_PASS=1: invoked exactly once on an ABORTED wake too: $(cat "$CALL_LOG3" 2>/dev/null)"

# ---------- real invocation (no stub): plain python3 suffices (note-fetch-views.py is pure-stdlib, no
# note_mcp/fastmcp import) -- proves the DEFAULT (non-test-injected) code path is itself runnable ----------
T4="$(mktemp -d)"
OUT4="$(ARTICLE_METRICS_PASS=1 ARTICLE_TEST=1 ARTICLE_DIR="$T4" AUTONOMY=off ARTICLE_TEST_TOPIC="AI agents" \
  ARTICLE_TEST_RESEARCH=sufficient ARTICLE_TEST_V0_RESULTS="PASS" ARTICLE_TEST_V05_RESULTS="PASS" \
  NOTE_LIVE_STATE_FILE="$T4/state/live-publishes.jsonl" ARTICLE_METRICS_STATE_FILE="$T4/state/article-metrics.jsonl" \
  bash "$SKILL/run.sh" 2>&1)"; rc4=$?
ok "$([ $rc4 -eq 0 ] && echo 1 || echo 0)" "real (non-stubbed) metrics pass runs without crashing the wake, rc=0 (rc=$rc4): $OUT4"
ok "$([ -f "$T4/state/metrics-pass.log" ] && echo 1 || echo 0)" "the real metrics pass's own output is captured to state/metrics-pass.log"

[ $fails -eq 0 ] && { echo "PASS -- FIND-006 fix: the metrics pass is wired into run.sh via an EXIT trap, opt-in (default off, zero impact on existing tests), fires on EVERY wake outcome (SKIPPED/ABORTED alike) when enabled, and the real (non-stubbed) invocation runs cleanly"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
