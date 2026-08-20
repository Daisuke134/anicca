#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GATE="$ROOT/scripts/editorial-gate.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin" "$TMP/run/gates"

cat >"$TMP/bin/model-runner" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
test "$1" = judge
test "$2" = --prompt-file
test "$3" = -
cat >/dev/null
printf 'CALL\n' >>"$FAKE_MODEL_CALLS"
printf '%s\n' "${ARTICLE_MODEL_REASONING_EFFORT:-unset}" >>"$FAKE_MODEL_EFFORTS"
printf '%s\n' \
  '{"verdict":"FAIL","fixes":["revise the article"],"strengths":[]}'
EOF
chmod +x "$TMP/bin/model-runner"

export ARTICLE_MODEL_RUNNER="$TMP/bin/model-runner"
export ARTICLE_RUN_DIR="$TMP/run"
export FAKE_MODEL_CALLS="$TMP/model-calls"
export FAKE_MODEL_EFFORTS="$TMP/model-efforts"
ARTICLE="$ARTICLE_RUN_DIR/article-ja.md"
printf '# Context ModeとCodex\n\n最初の本文。\n' >"$ARTICLE"

set +e
bash "$GATE" "$ARTICLE" --lang ja >"$TMP/first.out" 2>"$TMP/first.err"
first_rc=$?
set -e
[ "$first_rc" -eq 1 ]
[ "$(grep -c '^CALL$' "$FAKE_MODEL_CALLS")" -eq 1 ]

FIRST_HASH="$(shasum -a 256 "$ARTICLE" | awk '{print $1}')"
jq -e --arg hash "$FIRST_HASH" \
  '.verdict == "FAIL" and .article_sha256 == $hash and .requested_reasoning_effort == "medium"' \
  "$ARTICLE_RUN_DIR/gates/editorial-ja.json" >/dev/null
[ "$(sed -n '1p' "$FAKE_MODEL_EFFORTS")" = "medium" ]

set +e
bash "$GATE" "$ARTICLE" --lang ja >"$TMP/same.out" 2>"$TMP/same.err"
same_rc=$?
set -e
[ "$same_rc" -eq 76 ]
[ "$(grep -c '^CALL$' "$FAKE_MODEL_CALLS")" -eq 1 ]
grep -q "revision-required-before-rejudge" "$TMP/same.err"

printf '# Context ModeとCodex\n\n指摘を反映した本文。\n' >"$ARTICLE"
set +e
bash "$GATE" "$ARTICLE" --lang ja >"$TMP/revised.out" 2>"$TMP/revised.err"
revised_rc=$?
set -e
[ "$revised_rc" -eq 1 ]
[ "$(grep -c '^CALL$' "$FAKE_MODEL_CALLS")" -eq 2 ]

REVISED_HASH="$(shasum -a 256 "$ARTICLE" | awk '{print $1}')"
[ "$REVISED_HASH" != "$FIRST_HASH" ]
jq -e --arg hash "$REVISED_HASH" \
  '.verdict == "FAIL" and .article_sha256 == $hash and .requested_reasoning_effort == "high"' \
  "$ARTICLE_RUN_DIR/gates/editorial-ja.json" >/dev/null
[ "$(sed -n '2p' "$FAKE_MODEL_EFFORTS")" = "high" ]

printf '# Context ModeとCodex\n\nさらに変更した本文。\n' >"$ARTICLE"
set +e
bash "$GATE" "$ARTICLE" --lang ja >"$TMP/third.out" 2>"$TMP/third.err"
third_rc=$?
set -e
[ "$third_rc" -eq 77 ]
[ "$(grep -c '^CALL$' "$FAKE_MODEL_CALLS")" -eq 2 ]
[ "$(wc -l < "$FAKE_MODEL_EFFORTS" | tr -d ' ')" -eq 2 ]
grep -q "high-escalation-exhausted" "$TMP/third.err"

printf 'PASS: editorial FAIL permits one changed-draft Terra-high rejudge only\n'
