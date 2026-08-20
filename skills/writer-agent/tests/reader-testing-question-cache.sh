#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
GATE="$ROOT/skills/article-writer/scripts/reader-testing-gate.sh"
TEST_TMP="$(mktemp -d /tmp/article-reader-cache.XXXXXX)"
trap 'rm -rf -- "$TEST_TMP"' EXIT
mkdir -p "$TEST_TMP/bin"

cat >"$TEST_TMP/bin/model-runner" <<'FAKE'
#!/usr/bin/env bash
set -euo pipefail
test "$1" = judge
test "$2" = --prompt-file
test "$3" = -
prompt="$(cat)"
printf 'CALL\n' >>"$FAKE_CLAUDE_COUNT"
printf '%s\n===PROMPT-END===\n' "$prompt" >>"$FAKE_CLAUDE_LOG"
if [[ "$prompt" == *"generating a reader-testing question set"* ]]; then
  printf '%s\n' '{"questions":["Q1?","Q2?","Q3?","Q4?","Q5?"]}'
else
  printf '%s\n' '{"unanswered_questions":[]}'
fi
FAKE
chmod +x "$TEST_TMP/bin/model-runner"

export ARTICLE_MODEL_RUNNER="$TEST_TMP/bin/model-runner"
export FAKE_CLAUDE_COUNT="$TEST_TMP/calls"
export FAKE_CLAUDE_LOG="$TEST_TMP/prompts"
export ARTICLE_GATES_LOG="$TEST_TMP/gates.log"

ARTICLE="$TEST_TMP/article.md"
QUESTIONS="$TEST_TMP/questions-ja.json"
printf '# Title\n\nFirst version.\n' >"$ARTICLE"

# First cached run: generate once, persist, then judge.
: >"$FAKE_CLAUDE_COUNT"
: >"$FAKE_CLAUDE_LOG"
bash "$GATE" "$ARTICLE" --lang ja --questions-file "$QUESTIONS" >"$TEST_TMP/result-1.json"
test -f "$QUESTIONS"
test "$(jq '.questions | length' "$QUESTIONS")" -eq 5
test "$(grep -c '^CALL$' "$FAKE_CLAUDE_COUNT")" -eq 2

# Revised article: reuse byte-identical questions and call only the fresh answerer.
QUESTIONS_HASH="$(shasum -a 256 "$QUESTIONS" | awk '{print $1}')"
printf '# Title\n\nRevised version with the missing explanation.\n' >"$ARTICLE"
: >"$FAKE_CLAUDE_COUNT"
: >"$FAKE_CLAUDE_LOG"
bash "$GATE" "$ARTICLE" --lang ja --questions-file "$QUESTIONS" >"$TEST_TMP/result-2.json"
test "$(grep -c '^CALL$' "$FAKE_CLAUDE_COUNT")" -eq 1
test "$(shasum -a 256 "$QUESTIONS" | awk '{print $1}')" = "$QUESTIONS_HASH"
test "$(jq -c '.questions' "$TEST_TMP/result-1.json")" = "$(jq -c '.questions' "$TEST_TMP/result-2.json")"
! grep -q 'generating a reader-testing question set' "$FAKE_CLAUDE_LOG"

# Existing invalid cache: fail closed for this gate attempt, never overwrite/regenerate.
INVALID="$TEST_TMP/questions-invalid.json"
printf '{broken\n' >"$INVALID"
INVALID_HASH="$(shasum -a 256 "$INVALID" | awk '{print $1}')"
: >"$FAKE_CLAUDE_COUNT"
set +e
bash "$GATE" "$ARTICLE" --lang ja --questions-file "$INVALID" >"$TEST_TMP/result-invalid" 2>"$TEST_TMP/error-invalid"
INVALID_RC=$?
set -e
test "$INVALID_RC" -ne 0
test ! -s "$FAKE_CLAUDE_COUNT"
test "$(shasum -a 256 "$INVALID" | awk '{print $1}')" = "$INVALID_HASH"

# Backward-compatible one-shot call: generate in memory and judge, with no cache side effect.
LEGACY_CACHE="$TEST_TMP/legacy-should-not-exist.json"
: >"$FAKE_CLAUDE_COUNT"
bash "$GATE" "$ARTICLE" --lang en >"$TEST_TMP/result-legacy.json"
test "$(grep -c '^CALL$' "$FAKE_CLAUDE_COUNT")" -eq 2
test ! -e "$LEGACY_CACHE"

echo 'PASS: reader question cache is stable, fail-closed locally, and backward compatible'
