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
cat >"$CAPTURED_PROMPT"
printf '%s\n' \
  '{"verdict":"FAIL","fixes":["SkillOptの各事実を本文中の直接出典に結び付ける。末尾の出典一覧だけでは不十分。","比較値を追加する。"],"strengths":[]}'
EOF
chmod +x "$TMP/bin/model-runner"

export ARTICLE_MODEL_RUNNER="$TMP/bin/model-runner"
export ARTICLE_RUN_DIR="$TMP/run"
export CAPTURED_PROMPT="$TMP/prompt.txt"
ARTICLE="$ARTICLE_RUN_DIR/article-ja.md"
cat >"$ARTICLE" <<'EOF'
# SkillOptの検証

1. 実行結果を確認する。
2. 次の版と比較する。

## 出典

- https://github.com/microsoft/SkillOpt
EOF

set +e
bash "$GATE" "$ARTICLE" --lang ja >"$TMP/out.json" 2>"$TMP/err"
rc=$?
set -e
[ "$rc" -eq 1 ]

grep -q 'all URLs stay in one final Sources block' "$CAPTURED_PROMPT"
jq -e '
  .verdict == "FAIL"
  and (.fixes[0] | contains("Keep URLs in the single final Sources block"))
  and (.fixes[0] | contains("inline URLs"))
  and (.fixes[0] | contains("不十分") | not)
  and .fixes[1] == "比較値を追加する。"
  and .editorial_contract_reconciled == ["final_sources_block_preserved"]
' "$TMP/out.json" >/dev/null
jq -e '
  .editorial_contract_reconciled == ["final_sources_block_preserved"]
' "$ARTICLE_RUN_DIR/gates/editorial-ja.json" >/dev/null

printf 'PASS: editorial gate preserves the final Sources contract without faking PASS\n'
