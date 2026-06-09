#!/usr/bin/env bash
# eval-loop CLI: 4-dim weighted LLM-as-judge gate.
#
# Usage:
#   eval.sh <input.txt> <output.txt> [rubric.json]
#
# Emits a single JSON object on stdout:
#   {ts, backend, model, mode, task_class,
#    scores:{accuracy,helpfulness,harmlessness,coherence}, reasons:{...},
#    weights:{...}, threshold, total, pass, reason, elapsed_s}
#
# Env:
#   EVAL_MODE         "production" (default, fail-closed on heuristic) | "test"
#   EVAL_LOOP_NO_ENV  if "1", skip sourcing ~/.hermes/.env (test isolation)
#
# Exit codes:
#   0  → eval completed (PASS or FAIL — check `.pass` in the JSON; this is by design,
#        because the CALLER decides whether to block on FAIL. The pre-push hook does block.)
#   2  → bad arguments / unreadable file
#   3  → eval.py crashed (should never happen — eval.py is fail-closed)
set -uo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PY=/opt/homebrew/bin/python3
DEFAULT_RUBRIC="$SKILL_DIR/rubrics/default.rubric.json"

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
  echo '{"error":"usage: eval.sh <input.txt> <output.txt> [rubric.json]"}' >&2
  exit 2
fi

INPUT="$1"
OUTPUT="$2"
RUBRIC="${3:-$DEFAULT_RUBRIC}"

for f in "$INPUT" "$OUTPUT" "$RUBRIC"; do
  if [ ! -r "$f" ]; then
    printf '{"error":"unreadable: %s"}\n' "$f" >&2
    exit 2
  fi
done

# Auto-load ~/.hermes/.env if present (so judge backend key is available).
# Tests that need to exercise the all-backends-down / heuristic-only path
# set EVAL_LOOP_NO_ENV=1 to skip this sourcing — otherwise the .env would
# reintroduce real keys and prevent the heuristic path from being tested
# (codex P6 round 2 fix).
if [ -z "${EVAL_LOOP_NO_ENV:-}" ] && [ -r /Users/operator/.hermes/.env ]; then
  set -a; . /Users/operator/.hermes/.env; set +a
fi

if ! "$PY" "$SKILL_DIR/scripts/eval.py" "$INPUT" "$OUTPUT" "$RUBRIC"; then
  echo '{"error":"eval.py crashed — open an issue (this should not happen, eval.py is fail-closed)"}' >&2
  exit 3
fi
