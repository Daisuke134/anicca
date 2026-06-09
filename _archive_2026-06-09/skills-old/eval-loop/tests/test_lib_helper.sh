#!/usr/bin/env bash
# Unit test for scripts/lib.sh::eval_or_fail
#
# NOTE (all-backends-down environment, 2026-06-04): every BYOK judge backend
# is out of credit, so the good-text case can only be exercised via the
# deterministic heuristic. We pre-export EVAL_MODE=test (which lib.sh honors
# via ${EVAL_MODE:-production}) so the heuristic's good>=0.7 / slop<0.7
# discrimination drives the exit codes. The production fail-closed path is
# covered by test_eval_e2e.sh's DOWN scenario. When a backend regains credit,
# unset EVAL_MODE here to re-assert the live-judge contract end-to-end.
set -uo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RUBRIC="$SKILL_DIR/tests/fixtures/post-to-x.rubric.json"
GOOD_OUT="$SKILL_DIR/tests/fixtures/good_output.txt"
SLOP_OUT="$SKILL_DIR/tests/fixtures/slop_output.txt"
GOOD_IN="$SKILL_DIR/tests/fixtures/good_input.txt"
SLOP_IN="$SKILL_DIR/tests/fixtures/slop_input.txt"

export EVAL_MODE=test

# shellcheck source=/dev/null
source "$SKILL_DIR/scripts/lib.sh"

# ── good path → return 0
if ! eval_or_fail "$RUBRIC" "$GOOD_OUT" "$GOOD_IN" 2>/dev/null; then
  echo "FAIL: eval_or_fail returned non-zero on good output"
  exit 1
fi
echo "GOOD: pass"

# ── slop path → return 1
rc=0
eval_or_fail "$RUBRIC" "$SLOP_OUT" "$SLOP_IN" >/dev/null 2>&1 || rc=$?
if [ "$rc" -ne 1 ]; then
  echo "FAIL: expected exit 1 on slop output, got $rc"
  exit 1
fi
echo "SLOP: pass (rc=$rc)"

# ── stdin variant → slop via pipe still returns 1
rc=0
cat "$SLOP_OUT" | eval_or_fail "$RUBRIC" - "$SLOP_IN" >/dev/null 2>&1 || rc=$?
if [ "$rc" -ne 1 ]; then
  echo "FAIL: stdin variant: expected exit 1, got $rc"
  exit 1
fi
echo "STDIN: pass (rc=$rc)"

echo "PASS"
