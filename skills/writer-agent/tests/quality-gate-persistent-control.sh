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
  if [ "${FAIL_FINISH_PERSISTENCE:-0}" = 1 ]; then
    mkdir -p "$ARTICLE_RUN_DIR/gates/rubric-judge-en.terminal.json"
  fi
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
ARTICLE_SHA256="$(shasum -a 256 "$ARTICLE" | awk '{print $1}')"

# A pre-existing terminal artifact makes a resumed gate a zero-model-call no-op.
export ARTICLE_RUN_DIR="$TMP/legacy-run"
mkdir -p "$ARTICLE_RUN_DIR/gates"
printf '{"verdict":"PASS","final_score":80,"article_sha256":"%s"}\n' "$ARTICLE_SHA256" >"$ARTICLE_RUN_DIR/gates/rubric-judge-ja.json"
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

# Invalid attempt evidence must fail before invoking the model.
assert_begin_rejected() {
  local name="$1" relative_path="$2" payload="$3"
  export ARTICLE_RUN_DIR="$TMP/$name"
  mkdir -p "$(dirname "$ARTICLE_RUN_DIR/$relative_path")"
  printf '%s\n' "$payload" >"$ARTICLE_RUN_DIR/$relative_path"
  : >"$FAKE_CLAUDE_COUNT"
  set +e
  bash "$RUBRIC" "$ARTICLE" --lang ja >"$TMP/$name.out" 2>&1
  rc=$?
  set -e
  test "$rc" -eq 3
  test "$(grep -c '^CALL$' "$FAKE_CLAUDE_COUNT")" -eq 0
}
assert_begin_rejected state-malformed gates/.attempts/rubric-judge-ja.json not-json
assert_begin_rejected state-out-of-range gates/.attempts/rubric-judge-ja.json \
  "{\"gate\":\"rubric-judge\",\"lang\":\"ja\",\"attempts\":4,\"article_sha256\":\"$ARTICLE_SHA256\"}"
assert_begin_rejected terminal-malformed-pass gates/rubric-judge-ja.terminal.json \
  "{\"gate\":\"rubric-judge\",\"lang\":\"ja\",\"status\":\"pass\",\"article_sha256\":\"$ARTICLE_SHA256\"}"
assert_begin_rejected terminal-wrong-identity-pass gates/rubric-judge-ja.terminal.json \
  "{\"gate\":\"reader-testing-gate\",\"lang\":\"ja\",\"status\":\"pass\",\"attempts\":1,\"article_sha256\":\"$ARTICLE_SHA256\"}"
assert_begin_rejected terminal-contradictory-pass gates/rubric-judge-ja.terminal.json \
  "{\"gate\":\"rubric-judge\",\"lang\":\"ja\",\"status\":\"pass\",\"attempts\":1,\"exit_code\":1,\"article_sha256\":\"$ARTICLE_SHA256\",\"payload\":{\"verdict\":\"PASS\"}}"
assert_begin_rejected terminal-premature-advisory gates/rubric-judge-ja.terminal.json \
  "{\"gate\":\"rubric-judge\",\"lang\":\"ja\",\"status\":\"advisory\",\"attempts\":2,\"reason\":\"max-attempts-reached\",\"article_sha256\":\"$ARTICLE_SHA256\"}"

# A current legacy PASS cannot mask a current non-PASS terminal.
export ARTICLE_RUN_DIR="$TMP/legacy-terminal-conflict"
mkdir -p "$ARTICLE_RUN_DIR/gates"
printf '{"verdict":"PASS","article_sha256":"%s"}\n' "$ARTICLE_SHA256" \
  >"$ARTICLE_RUN_DIR/gates/rubric-judge-ja.json"
printf '{"gate":"rubric-judge","lang":"ja","status":"advisory","attempts":3,"reason":"max-attempts-reached","article_sha256":"%s"}\n' "$ARTICLE_SHA256" \
  >"$ARTICLE_RUN_DIR/gates/rubric-judge-ja.terminal.json"
: >"$FAKE_CLAUDE_COUNT"
set +e
bash "$RUBRIC" "$ARTICLE" --lang ja >"$TMP/legacy-terminal-conflict.out" 2>&1
rc=$?
set -e
test "$rc" -eq 3
test "$(grep -c '^CALL$' "$FAKE_CLAUDE_COUNT")" -eq 0

# A current PASS terminal cannot override a conflicting state attempt count.
export ARTICLE_RUN_DIR="$TMP/state-pass-mismatch"
mkdir -p "$ARTICLE_RUN_DIR/gates/.attempts"
printf '{"gate":"rubric-judge","lang":"ja","attempts":3,"article_sha256":"%s"}\n' "$ARTICLE_SHA256" \
  >"$ARTICLE_RUN_DIR/gates/.attempts/rubric-judge-ja.json"
printf '{"gate":"rubric-judge","lang":"ja","status":"pass","attempts":1,"exit_code":0,"article_sha256":"%s","payload":{"verdict":"PASS"}}\n' "$ARTICLE_SHA256" \
  >"$ARTICLE_RUN_DIR/gates/rubric-judge-ja.terminal.json"
: >"$FAKE_CLAUDE_COUNT"
set +e
bash "$RUBRIC" "$ARTICLE" --lang ja >"$TMP/state-pass-mismatch.out" 2>&1
rc=$?
set -e
test "$rc" -eq 3
test "$(grep -c '^CALL$' "$FAKE_CLAUDE_COUNT")" -eq 0

# A PASS from the model is not successful if finish persistence fails.
export ARTICLE_RUN_DIR="$TMP/pass-finish-failure-run"
export FAKE_RUBRIC_PASS=1
export FAIL_FINISH_PERSISTENCE=1
: >"$FAKE_CLAUDE_COUNT"
set +e
bash "$RUBRIC" "$ARTICLE" --lang en >"$TMP/pass-finish-failure.out" 2>&1
rc=$?
set -e
test "$rc" -eq 3
test "$(grep -c '^CALL$' "$FAKE_CLAUDE_COUNT")" -eq 1
test -d "$ARTICLE_RUN_DIR/gates/rubric-judge-en.terminal.json"
unset FAIL_FINISH_PERSISTENCE
unset FAKE_RUBRIC_PASS

# finish cannot write an unbounded terminal attempt.
export ARTICLE_RUN_DIR="$TMP/finish-out-of-range"
mkdir -p "$ARTICLE_RUN_DIR/gates"
set +e
python3 "$ROOT/skills/writer-agent/scripts/gate-attempt-control.py" finish \
  --run-dir "$ARTICLE_RUN_DIR" --gate rubric-judge --lang ja --markdown-file "$ARTICLE" \
  --attempt 4 --exit-code 1 >"$TMP/finish-out-of-range.out" 2>&1
rc=$?
set -e
test "$rc" -eq 2
test ! -e "$ARTICLE_RUN_DIR/gates/rubric-judge-ja.terminal.json"

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

# A same-hash terminal remains capped with missing or stale attempt state.
RECOVERY_SHA256="$(shasum -a 256 "$ARTICLE" | awk '{print $1}')"
check_terminal_cap() {
  local name="$1" stale="${2:-0}"
  export ARTICLE_RUN_DIR="$TMP/$name"
  mkdir -p "$ARTICLE_RUN_DIR/gates"
  printf '{"gate":"reader-testing-gate","lang":"en","status":"revision-required","attempts":3,"exit_code":1,"article_sha256":"%s"}\n' "$RECOVERY_SHA256" \
    >"$ARTICLE_RUN_DIR/gates/reader-testing-gate-en.terminal.json"
  if [ "$stale" -eq 1 ]; then
    mkdir -p "$ARTICLE_RUN_DIR/gates/.attempts"
    printf '%s\n' '{"gate":"reader-testing-gate","lang":"en","attempts":0,"article_sha256":"0000000000000000000000000000000000000000000000000000000000000000"}' \
      >"$ARTICLE_RUN_DIR/gates/.attempts/reader-testing-gate-en.json"
  fi
  : >"$FAKE_CLAUDE_COUNT"
  set +e
  bash "$READER" "$ARTICLE" --lang en >"$TMP/$name.out" 2>&1
  rc=$?
  set -e
  test "$rc" -eq 75
  test "$(grep -c '^CALL$' "$FAKE_CLAUDE_COUNT")" -eq 0
  jq -e '.status == "advisory" and .attempts == 3' \
    "$ARTICLE_RUN_DIR/gates/reader-testing-gate-en.terminal.json" >/dev/null
}
check_terminal_cap reader-terminal-missing
check_terminal_cap reader-terminal-stale 1

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
