#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
RUBRIC="$ROOT/skills/writer-agent/scripts/rubric-judge.sh"
READER="$ROOT/skills/writer-agent/scripts/reader-testing-gate.sh"
TMP="$(mktemp -d /tmp/article-gate-control.XXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
mkdir -p "$TMP/bin"

cat >"$TMP/bin/model-runner" <<'FAKE'
#!/usr/bin/env bash
set -euo pipefail
test "$1" = judge
test "$2" = --prompt-file
test "$3" = -
prompt="$(cat)"
printf 'CALL\n' >>"$FAKE_CLAUDE_COUNT"
if [[ "$prompt" == *"generating a reader-testing question set"* ]]; then
  printf '%s\n' '{"questions":["Q1?","Q2?","Q3?","Q4?","Q5?"]}'
elif [[ "$prompt" == *"first-time reader with ZERO other context"* ]]; then
  printf '%s\n' '{"unanswered_questions":["Q1?"]}'
elif [ "${FAKE_RUBRIC_PASS:-0}" = 1 ]; then
  printf '%s\n' '{"scores":{"lead":20,"one_reader":20,"promise":20,"why_pay":20,"jargon_defined":20},"positive_total":100,"deductions":[],"final_score":100,"improvements":[]}'
else
  printf '%s\n' '{"scores":{"lead":0,"one_reader":0,"promise":0,"why_pay":0,"jargon_defined":0},"positive_total":0,"deductions":[],"final_score":0,"improvements":["revise"]}'
fi
FAKE
chmod +x "$TMP/bin/model-runner"
export ARTICLE_MODEL_RUNNER="$TMP/bin/model-runner"
export FAKE_CLAUDE_COUNT="$TMP/calls"
export ARTICLE_GATES_LOG="$TMP/gates.log"
ARTICLE="$TMP/article.md"
printf '# Title\n\nBody.\n' >"$ARTICLE"

# A pre-existing terminal artifact makes a resumed gate a zero-model-call no-op.
export ARTICLE_RUN_DIR="$TMP/legacy-run"
mkdir -p "$ARTICLE_RUN_DIR/gates"
printf '%s\n' '{"verdict":"PASS","final_score":80}' >"$ARTICLE_RUN_DIR/gates/rubric-judge-ja.json"
: >"$FAKE_CLAUDE_COUNT"
bash "$RUBRIC" "$ARTICLE" --lang ja >"$TMP/legacy.out"
test ! -s "$FAKE_CLAUDE_COUNT"
jq -e '.verdict == "PASS"' "$TMP/legacy.out" >/dev/null

# A legacy FAIL is an evaluation result, not proof that all three attempts were spent.
export ARTICLE_RUN_DIR="$TMP/legacy-fail-run"
mkdir -p "$ARTICLE_RUN_DIR/gates"
printf '%s\n' '{"verdict":"FAIL","final_score":40}' >"$ARTICLE_RUN_DIR/gates/rubric-judge-ja.json"
: >"$FAKE_CLAUDE_COUNT"
set +e
bash "$RUBRIC" "$ARTICLE" --lang ja >"$TMP/legacy-fail.out" 2>&1
rc=$?
set -e
test "$rc" -eq 1
test "$(grep -c '^CALL$' "$FAKE_CLAUDE_COUNT")" -eq 1

# A failing rubric may execute at most three model evaluations for one run/lang.
export ARTICLE_RUN_DIR="$TMP/rubric-run"
: >"$FAKE_CLAUDE_COUNT"
for expected in 1 2 3; do
  set +e
  bash "$RUBRIC" "$ARTICLE" --lang ja >"$TMP/rubric-$expected.out" 2>&1
  rc=$?
  set -e
  test "$rc" -eq 1
  test "$(grep -c '^CALL$' "$FAKE_CLAUDE_COUNT")" -eq "$expected"
done
set +e
bash "$RUBRIC" "$ARTICLE" --lang ja >"$TMP/rubric-4.out" 2>&1
rc=$?
set -e
test "$rc" -eq 75
test "$(grep -c '^CALL$' "$FAKE_CLAUDE_COUNT")" -eq 3
jq -e '.status == "advisory" and .attempts == 3' "$ARTICLE_RUN_DIR/gates/rubric-judge-ja.terminal.json" >/dev/null

# PASS is terminal too: the second invocation reuses evidence without a model call.
export ARTICLE_RUN_DIR="$TMP/pass-run"
export FAKE_RUBRIC_PASS=1
: >"$FAKE_CLAUDE_COUNT"
bash "$RUBRIC" "$ARTICLE" --lang en >"$TMP/pass-1.out"
bash "$RUBRIC" "$ARTICLE" --lang en >"$TMP/pass-2.out"
test "$(grep -c '^CALL$' "$FAKE_CLAUDE_COUNT")" -eq 1
jq -e '.status == "pass" and .attempts == 1' "$ARTICLE_RUN_DIR/gates/rubric-judge-en.terminal.json" >/dev/null
printf '\nChanged after PASS.\n' >>"$ARTICLE"
bash "$RUBRIC" "$ARTICLE" --lang en >"$TMP/pass-3-changed.out"
test "$(grep -c '^CALL$' "$FAKE_CLAUDE_COUNT")" -eq 2
unset FAKE_RUBRIC_PASS

# Reader questions stay fixed and the answer judge also stops after three evaluations.
export ARTICLE_RUN_DIR="$TMP/reader-run"
QUESTIONS="$ARTICLE_RUN_DIR/gates/reader-questions-en.json"
: >"$FAKE_CLAUDE_COUNT"
for expected_calls in 2 3 4; do
  set +e
  bash "$READER" "$ARTICLE" --lang en --questions-file "$QUESTIONS" >"$TMP/reader-$expected_calls.out" 2>&1
  rc=$?
  set -e
  test "$rc" -eq 1
  test "$(grep -c '^CALL$' "$FAKE_CLAUDE_COUNT")" -eq "$expected_calls"
done
QUESTIONS_HASH="$(shasum -a 256 "$QUESTIONS" | awk '{print $1}')"
set +e
bash "$READER" "$ARTICLE" --lang en --questions-file "$QUESTIONS" >"$TMP/reader-4.out" 2>&1
rc=$?
set -e
test "$rc" -eq 75
test "$(grep -c '^CALL$' "$FAKE_CLAUDE_COUNT")" -eq 4
test "$(shasum -a 256 "$QUESTIONS" | awk '{print $1}')" = "$QUESTIONS_HASH"
jq -e '.status == "advisory" and .attempts == 3' "$ARTICLE_RUN_DIR/gates/reader-testing-gate-en.terminal.json" >/dev/null

echo 'PASS: rubric and reader gates persist a three-evaluation cap and skip terminal resumes'
