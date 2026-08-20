#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GATE="$ROOT/scripts/bookmark-gate.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cat >"$TMP/actionable-ja.md" <<'EOF'
## 導入前に測る

1. doctorで保存先とSQLiteを確認する。
2. indexで代表的なログを登録する。
3. searchで既知の答えを探し、全文と比較する。
EOF

bash "$GATE" \
  "Context ModeとCodexで大きな出力を減らす" \
  "$TMP/actionable-ja.md" \
  --lang ja

# Production replacement run 20260729-173948 used a native Japanese title
# whose concrete anchors are an acronym plus two katakana terms. Requiring
# two English Title Case words rejects it for script shape, not bookmark value.
bash "$GATE" \
  "テストが緑でも、AIエージェントのループは学んでいない。証拠をつなぐ方法" \
  "$TMP/actionable-ja.md" \
  --lang ja

cat >"$TMP/non-actionable-ja.md" <<'EOF'
Context ModeとCodexには2026年も多くの利用者がいる。
SQLiteを使う設計には複数の利点がある。
EOF

set +e
non_actionable_output="$(
  bash "$GATE" \
    "Context ModeとCodexの現在" \
    "$TMP/non-actionable-ja.md" \
    --lang ja 2>&1
)"
non_actionable_rc=$?
set -e

[ "$non_actionable_rc" -eq 1 ]
printf '%s' "$non_actionable_output" | grep -q "FAIL not actionable"

cat >"$TMP/actionable-en.md" <<'EOF'
## How to verify it

Step 1: run doctor.
Step 2: compare the result.
EOF

bash "$GATE" \
  "Context Mode and Codex in 2 steps" \
  "$TMP/actionable-en.md" \
  --lang en

printf 'PASS: bookmark gate is language-aware without accepting numeric prose\n'
