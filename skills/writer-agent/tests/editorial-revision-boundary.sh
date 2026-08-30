#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GATE="$ROOT/scripts/editorial-gate.sh"
TMP="$(cd "$(mktemp -d)" && pwd -P)"
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
mkdir -p "$TMP/relative/gates"
printf '# Relative article\n\nFirst evaluation.\n' >"$TMP/relative/article-ja.md"
export FAKE_MODEL_CALLS="$TMP/model-calls"
export FAKE_MODEL_EFFORTS="$TMP/model-efforts"
: >"$FAKE_MODEL_CALLS"
: >"$FAKE_MODEL_EFFORTS"
set +e
(cd "$TMP" && env -u ARTICLE_RUN_DIR bash "$GATE" relative/article-ja.md --lang ja \
  >"$TMP/relative.out" 2>"$TMP/relative.err")
relative_rc=$?
set -e
[ "$relative_rc" -eq 1 ]
[ "$(grep -c '^CALL$' "$FAKE_MODEL_CALLS")" -eq 1 ]

: >"$FAKE_MODEL_CALLS"
: >"$FAKE_MODEL_EFFORTS"
export ARTICLE_RUN_DIR="$TMP/run"
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

# A real quality-repair owner may authorize one changed-hash high rejudge only
# while the repair controller is invoking this run and its owner is an
# ancestor of the gate process.
printf '{"version":1,"status":"invoking","run_id":"%s","quality_action":"evaluate_reroute","owner_pid":%s}\n' \
  "$(basename "$ARTICLE_RUN_DIR")" "$$" >"$ARTICLE_RUN_DIR/gates/quality-repair-state.json"
export ARTICLE_QUALITY_REPAIR_ACTIVE=1
export ARTICLE_QUALITY_REPAIR_OWNER_PID="$$"
set +e
bash "$GATE" "$ARTICLE" --lang ja >"$TMP/repair.out" 2>"$TMP/repair.err"
repair_rc=$?
set -e
[ "$repair_rc" -eq 1 ]
[ "$(grep -c '^CALL$' "$FAKE_MODEL_CALLS")" -eq 3 ]
THIRD_HASH="$(shasum -a 256 "$ARTICLE" | awk '{print $1}')"
[ -d "$ARTICLE_RUN_DIR/gates/.attempts/editorial-high-ja/$THIRD_HASH" ]
jq -e --arg hash "$THIRD_HASH" \
  '.verdict == "FAIL" and .article_sha256 == $hash and .requested_reasoning_effort == "high"' \
  "$ARTICLE_RUN_DIR/gates/editorial-ja.json" >/dev/null

# The active fallback must authorize only the selected run's canonical article.
mkdir -p "$TMP/other-run"
printf '# Context ModeとCodex\n\n別runの本文。\n' >"$TMP/other-run/article-ja.md"
set +e
bash "$GATE" "$TMP/other-run/article-ja.md" --lang ja >"$TMP/alternate.out" 2>"$TMP/alternate.err"
alternate_rc=$?
set -e
[ "$alternate_rc" -eq 77 ]
[ "$(grep -c '^CALL$' "$FAKE_MODEL_CALLS")" -eq 3 ]

# A regular receipt from another run cannot authorize this hash.
printf '# Context ModeとCodex\n\n正規cross-run receiptを拒否する変更。\n' >"$ARTICLE"
CROSS_RUN_HASH="$(shasum -a 256 "$ARTICLE" | awk '{print $1}')"
printf '{"version":2,"run_id":"other-run","attempt":2,"action":"evaluate_reroute","quality":{"ja":{"article_sha256":"%s"}}}\n' \
  "$CROSS_RUN_HASH" >"$ARTICLE_RUN_DIR/gates/quality-self-heal.json"
set +e
bash "$GATE" "$ARTICLE" --lang ja >"$TMP/cross-run.out" 2>"$TMP/cross-run.err"
cross_run_rc=$?
set -e
[ "$cross_run_rc" -eq 77 ]
[ "$(grep -c '^CALL$' "$FAKE_MODEL_CALLS")" -eq 3 ]
rm -f "$ARTICLE_RUN_DIR/gates/quality-self-heal.json"

# A symlink receipt is not evidence, even if its target has the right bytes.
printf '{"version":2,"run_id":"%s","attempt":2,"action":"evaluate_reroute","quality":{"ja":{"article_sha256":"%s"}}}\n' \
  "$(basename "$ARTICLE_RUN_DIR")" "$CROSS_RUN_HASH" >"$TMP/canonical-receipt.json"
ln -s "$TMP/canonical-receipt.json" "$ARTICLE_RUN_DIR/gates/quality-self-heal.json"
set +e
bash "$GATE" "$ARTICLE" --lang ja >"$TMP/symlink-receipt.out" 2>"$TMP/symlink-receipt.err"
symlink_receipt_rc=$?
set -e
[ "$symlink_receipt_rc" -eq 77 ]
[ "$(grep -c '^CALL$' "$FAKE_MODEL_CALLS")" -eq 3 ]
rm -f "$ARTICLE_RUN_DIR/gates/quality-self-heal.json"

# A live but unrelated process is not a repair owner.
sleep 60 &
unrelated_pid=$!
printf '{"version":1,"status":"invoking","run_id":"%s","quality_action":"evaluate_reroute","owner_pid":%s}\n' \
  "$(basename "$ARTICLE_RUN_DIR")" "$unrelated_pid" >"$ARTICLE_RUN_DIR/gates/quality-repair-state.json"
export ARTICLE_QUALITY_REPAIR_OWNER_PID="$unrelated_pid"
printf '# Context ModeとCodex\n\n無関係PIDを拒否する変更。\n' >"$ARTICLE"
set +e
bash "$GATE" "$ARTICLE" --lang ja >"$TMP/unrelated.out" 2>"$TMP/unrelated.err"
unrelated_rc=$?
set -e
kill "$unrelated_pid" 2>/dev/null || true
wait "$unrelated_pid" 2>/dev/null || true
[ "$unrelated_rc" -eq 77 ]
[ "$(grep -c '^CALL$' "$FAKE_MODEL_CALLS")" -eq 3 ]

# Restore a valid repair state for the path-boundary cases below.
printf '{"version":1,"status":"invoking","run_id":"%s","quality_action":"evaluate_reroute","owner_pid":%s}\n' \
  "$(basename "$ARTICLE_RUN_DIR")" "$$" >"$ARTICLE_RUN_DIR/gates/quality-repair-state.json"
export ARTICLE_QUALITY_REPAIR_OWNER_PID="$$"

# A valid receipt under a symlinked run directory is still rejected because
# the selected run's physical path must equal its lexical path.
CANONICAL_PARENT="$TMP/canonical-parent"
ln -s "$TMP" "$CANONICAL_PARENT"
export ARTICLE_RUN_DIR="$CANONICAL_PARENT/run"
ARTICLE="$ARTICLE_RUN_DIR/article-ja.md"
printf '# Context ModeとCodex\n\nsymlink run directory。\n' >"$ARTICLE"
SYMLINK_RUN_HASH="$(shasum -a 256 "$ARTICLE" | awk '{print $1}')"
printf '{"version":2,"run_id":"run","attempt":2,"action":"evaluate_reroute","quality":{"ja":{"article_sha256":"%s"}}}\n' \
  "$SYMLINK_RUN_HASH" >"$ARTICLE_RUN_DIR/gates/quality-self-heal.json"
set +e
bash "$GATE" "$ARTICLE" --lang ja >"$TMP/symlink-run.out" 2>"$TMP/symlink-run.err"
symlink_run_rc=$?
set -e
[ "$symlink_run_rc" -eq 77 ]
[ "$(grep -c '^CALL$' "$FAKE_MODEL_CALLS")" -eq 3 ]
rm -f "$ARTICLE_RUN_DIR/gates/quality-self-heal.json"
export ARTICLE_RUN_DIR="$TMP/run"
ARTICLE="$ARTICLE_RUN_DIR/article-ja.md"

# A symlink repair-state file cannot authorize the active fallback.
printf '# Context ModeとCodex\n\nsymlink repair state。\n' >"$ARTICLE"
cp "$ARTICLE_RUN_DIR/gates/quality-repair-state.json" "$TMP/repair-state.json"
rm -f "$ARTICLE_RUN_DIR/gates/quality-repair-state.json"
ln -s "$TMP/repair-state.json" "$ARTICLE_RUN_DIR/gates/quality-repair-state.json"
set +e
bash "$GATE" "$ARTICLE" --lang ja >"$TMP/symlink-state.out" 2>"$TMP/symlink-state.err"
symlink_state_rc=$?
set -e
[ "$symlink_state_rc" -eq 77 ]
[ "$(grep -c '^CALL$' "$FAKE_MODEL_CALLS")" -eq 3 ]
rm -f "$ARTICLE_RUN_DIR/gates/quality-repair-state.json"
mv "$TMP/repair-state.json" "$ARTICLE_RUN_DIR/gates/quality-repair-state.json"

# A symlinked final run directory cannot authorize the fallback either.
RUN_ALIAS="$TMP/run-alias"
ln -s "$ARTICLE_RUN_DIR" "$RUN_ALIAS"
export ARTICLE_RUN_DIR="$RUN_ALIAS"
ARTICLE="$ARTICLE_RUN_DIR/article-ja.md"
printf '# Context ModeとCodex\n\nsymlink final run。\n' >"$ARTICLE"
set +e
bash "$GATE" "$ARTICLE" --lang ja >"$TMP/symlink-final-run.out" 2>"$TMP/symlink-final-run.err"
symlink_final_run_rc=$?
set -e
[ "$symlink_final_run_rc" -eq 77 ]
[ "$(grep -c '^CALL$' "$FAKE_MODEL_CALLS")" -eq 3 ]
rm -f "$RUN_ALIAS"
export ARTICLE_RUN_DIR="$TMP/run"
ARTICLE="$ARTICLE_RUN_DIR/article-ja.md"

# A non-owner PID also fails closed after the path checks pass.
printf '# Context ModeとCodex\n\nowner PIDを拒否する変更。\n' >"$ARTICLE"
export ARTICLE_QUALITY_REPAIR_OWNER_PID=999999999
printf '{"version":1,"status":"invoking","run_id":"%s","quality_action":"evaluate_reroute","owner_pid":999999999}\n' \
  "$(basename "$ARTICLE_RUN_DIR")" >"$ARTICLE_RUN_DIR/gates/quality-repair-state.json"
set +e
bash "$GATE" "$ARTICLE" --lang ja >"$TMP/nonowner.out" 2>"$TMP/nonowner.err"
nonowner_rc=$?
set -e
[ "$nonowner_rc" -eq 77 ]
[ "$(grep -c '^CALL$' "$FAKE_MODEL_CALLS")" -eq 3 ]

# The canonical receipt is the reviewed production-shaped authorization.
export ARTICLE_QUALITY_REPAIR_OWNER_PID="$$"
printf '# Context ModeとCodex\n\ncanonical receiptで再評価する変更。\n' >"$ARTICLE"
CANONICAL_HASH="$(shasum -a 256 "$ARTICLE" | awk '{print $1}')"
printf '{"version":2,"run_id":"%s","attempt":2,"action":"evaluate_reroute","quality":{"ja":{"article_sha256":"%s"}}}\n' \
  "$(basename "$ARTICLE_RUN_DIR")" "$CANONICAL_HASH" >"$ARTICLE_RUN_DIR/gates/quality-self-heal.json"
set +e
bash "$GATE" "$ARTICLE" --lang ja >"$TMP/canonical.out" 2>"$TMP/canonical.err"
canonical_rc=$?
set -e
[ "$canonical_rc" -eq 1 ]
[ "$(grep -c '^CALL$' "$FAKE_MODEL_CALLS")" -eq 4 ]
jq -e --arg hash "$CANONICAL_HASH" \
  '.verdict == "FAIL" and .article_sha256 == $hash and .requested_reasoning_effort == "high"' \
  "$ARTICLE_RUN_DIR/gates/editorial-ja.json" >/dev/null

printf 'PASS: editorial FAIL permits one changed-draft Terra-high rejudge only\n'
