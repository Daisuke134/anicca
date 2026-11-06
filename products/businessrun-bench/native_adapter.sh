#!/usr/bin/env bash
# Local development cell. Current Codex account/model defaults; no benchmark model override.
set -euo pipefail
ws=$1
prompt_file=$2
out=$3
codex_bin=${CODEX_BIN:-codex}
instruction="$(cat "$prompt_file")

この試行は合成ERPの業務評価です。渡されたworkspace内のhandbookとERP_URL/ERP_TOKEN、erp CLIだけで依頼を処理してください。採点コード・参照解答・他の試行・個人ファイル・外部サービスを参照しないでください。実世界の送信/課金/設定変更は禁止です。"
cd "$ws"
exec "$codex_bin" exec -C "$ws" --skip-git-repo-check --ephemeral --json \
  --disable apps --disable plugins --sandbox workspace-write \
  -c 'sandbox_workspace_write.network_access=true' -c 'approval_policy="never"' \
  -o "$out/last_message.txt" "$instruction" < /dev/null > "$out/codex_events.jsonl"
