#!/usr/bin/env bash
# E2E: run eval.sh against (a) good output, (b) slop output, (c) all-backends-down,
# assert pass/fail per Wave 1 done-condition.
#
# JUDGE BACKEND (2026-06-04): scenarios 1/2 run LIVE through HermesJudge — the
# default Wave-1 judge that shells out to `hermes chat -Q -q` (Hermes provider
# pinned to copilot/gpt-4o-mini per #323, free via the gh auth subscription, no
# per-token billing). This works even though every BYOK key in ~/.hermes/.env
# (OpenAI/DeepSeek/Anthropic/Gemini/Kimi) is out of credit. So DC2/DC3 are
# verified with a REAL LLM judge, not the heuristic.
#
# The all-backends-down scenarios (3/3b) set EVAL_LOOP_NO_HERMES_JUDGE=1 IN
# ADDITION to unsetting the BYOK keys, so even the free Hermes judge is
# disabled and the heuristic path is genuinely exercised: scenario 3 proves the
# EVAL_MODE=production fail-closed contract (heuristic → pass:false), scenario
# 3b proves the heuristic still discriminates good>slop in EVAL_MODE=test.
#
# Set EVAL_E2E_NO_LIVE=1 to force scenarios 1/2 onto the heuristic (offline CI
# without hermes); they then assert the good>=0.7 / slop<0.7 heuristic ranking.
set -uo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RUBRIC="$SKILL_DIR/tests/fixtures/post-to-x.rubric.json"
GOOD_IN="$SKILL_DIR/tests/fixtures/good_input.txt"
GOOD_OUT="$SKILL_DIR/tests/fixtures/good_output.txt"
SLOP_IN="$SKILL_DIR/tests/fixtures/slop_input.txt"
SLOP_OUT="$SKILL_DIR/tests/fixtures/slop_output.txt"
EVAL="$SKILL_DIR/scripts/eval.sh"
JQ=/usr/bin/jq

# Scenarios 1/2: LIVE HermesJudge by default. EVAL_E2E_NO_LIVE=1 forces the
# offline heuristic (test mode + all judges disabled) for hermes-less CI.
if [ -n "${EVAL_E2E_NO_LIVE:-}" ]; then
  SCEN12_PREFIX="EVAL_LOOP_NO_ENV=1 EVAL_LOOP_NO_HERMES_JUDGE=1 EVAL_MODE=test OPENAI_API_KEY= DEEPSEEK_API_KEY= ANTHROPIC_API_KEY= GEMINI_API_KEY= GOOGLE_API_KEY= XAI_API_KEY= MOONSHOT_API_KEY= KIMI_API_KEY="
else
  SCEN12_PREFIX=""
fi

# All judges down (BYOK unset + Hermes disabled) for the fail-closed scenarios.
ALL_DOWN="EVAL_LOOP_NO_ENV=1 EVAL_LOOP_NO_HERMES_JUDGE=1 OPENAI_API_KEY= DEEPSEEK_API_KEY= ANTHROPIC_API_KEY= GEMINI_API_KEY= GOOGLE_API_KEY= XAI_API_KEY= MOONSHOT_API_KEY= KIMI_API_KEY="

fail() { echo "FAIL: $*"; exit 1; }

# ── 1. good input → pass=true, total >= 0.7
RES="$(env $SCEN12_PREFIX "$EVAL" "$GOOD_IN" "$GOOD_OUT" "$RUBRIC")" || fail "eval.sh exited non-zero on good input"
echo "$RES" | "$JQ" -e '.pass == true' >/dev/null || fail "good: pass != true (got $(echo "$RES" | "$JQ" -c .))"
echo "$RES" | "$JQ" -e '.total >= 0.7' >/dev/null || fail "good: total < 0.7 (got $(echo "$RES" | "$JQ" -c .))"
echo "$RES" | "$JQ" -e '.scores | (has("accuracy") and has("helpfulness") and has("harmlessness") and has("coherence"))' >/dev/null \
  || fail "good: missing one of 4 dim scores"
echo "GOOD: $(echo "$RES" | "$JQ" -c '.total, .scores, .backend')"

# ── 2. slop input → pass=false, total < 0.7
RES="$(env $SCEN12_PREFIX "$EVAL" "$SLOP_IN" "$SLOP_OUT" "$RUBRIC")" || fail "eval.sh exited non-zero on slop input"
echo "$RES" | "$JQ" -e '.pass == false' >/dev/null || fail "slop: pass != false (got $(echo "$RES" | "$JQ" -c .))"
echo "$RES" | "$JQ" -e '.total < 0.7' >/dev/null || fail "slop: total >= 0.7 (got $(echo "$RES" | "$JQ" -c .))"
echo "SLOP: $(echo "$RES" | "$JQ" -c '.total, .scores, .backend')"

# ── 3. all backends down → still returns valid JSON with backend="heuristic"
# EVAL_LOOP_NO_ENV=1 skips sourcing ~/.hermes/.env so the unset keys stick;
# EVAL_LOOP_NO_HERMES_JUDGE=1 disables the free Hermes judge too — together they
# force the heuristic path. EVAL_MODE=production forces the fail-closed
# contract: heuristic backend → pass:false ALWAYS.
RES="$(env $ALL_DOWN EVAL_MODE=production "$EVAL" "$GOOD_IN" "$GOOD_OUT" "$RUBRIC")" \
  || fail "eval.sh exited non-zero in all-backends-down mode (must fail closed, not crash)"
echo "$RES" | "$JQ" -e '.backend == "heuristic"' >/dev/null || fail "down: backend != heuristic (got $(echo "$RES" | "$JQ" -c .backend))"
echo "$RES" | "$JQ" -e 'has("pass") and has("total") and has("scores")' >/dev/null \
  || fail "down: missing required keys"
# Production-mode contract: heuristic → pass:false (no good-text escape hatch)
echo "$RES" | "$JQ" -e '.pass == false' >/dev/null \
  || fail "down: production mode must return pass:false on heuristic (got $(echo "$RES" | "$JQ" -c .))"
echo "$RES" | "$JQ" -e '.reason == "all backends down"' >/dev/null \
  || fail "down: production mode must set reason=\"all backends down\" (got $(echo "$RES" | "$JQ" -c .reason))"
echo "DOWN: $(echo "$RES" | "$JQ" -c '.total, .backend, .pass, .reason')"

# ── 3b. all backends down + EVAL_MODE=test → heuristic differentiates good from slop
RES="$(env $ALL_DOWN EVAL_MODE=test "$EVAL" "$GOOD_IN" "$GOOD_OUT" "$RUBRIC")" \
  || fail "eval.sh exited non-zero in all-backends-down (test mode)"
echo "$RES" | "$JQ" -e '.backend == "heuristic"' >/dev/null || fail "down-test: backend != heuristic"
echo "$RES" | "$JQ" -e 'has("pass") and has("total")' >/dev/null || fail "down-test: missing keys"
GOOD_TOTAL_TEST="$(echo "$RES" | "$JQ" -r '.total')"
echo "DOWN-TEST GOOD: $(echo "$RES" | "$JQ" -c '.total, .backend, .pass')"

RES="$(env $ALL_DOWN EVAL_MODE=test "$EVAL" "$SLOP_IN" "$SLOP_OUT" "$RUBRIC")" \
  || fail "eval.sh exited non-zero on slop (test mode)"
SLOP_TOTAL_TEST="$(echo "$RES" | "$JQ" -r '.total')"
echo "DOWN-TEST SLOP: $(echo "$RES" | "$JQ" -c '.total, .backend, .pass')"
# The heuristic MUST score slop strictly below good (proves the offline scorer discriminates).
awk -v g="$GOOD_TOTAL_TEST" -v s="$SLOP_TOTAL_TEST" 'BEGIN{ exit !(s < g) }' \
  || fail "down-test: heuristic did not rank slop ($SLOP_TOTAL_TEST) below good ($GOOD_TOTAL_TEST)"

# ── 4. cost log appended at least 5 rows (good, slop, down-prod, down-test-good, down-test-slop)
LOG=/Users/anicca/.hermes/state/eval-cost.jsonl
LINES=$(wc -l < "$LOG" 2>/dev/null || echo 0)
[ "$LINES" -ge 5 ] || fail "cost log has $LINES lines, expected >= 5"
tail -n 1 "$LOG" | "$JQ" -e '.ts and .dim_count == 4 and (.backend == "hermes_copilot" or .backend == "openai" or .backend == "deepseek" or .backend == "anthropic" or .backend == "gemini" or .backend == "kimi" or .backend == "heuristic")' >/dev/null \
  || fail "cost log row malformed: $(tail -n 1 "$LOG")"

echo "PASS"
