#!/usr/bin/env bash
# VPS上で実行するスクリプト。openai-codex OAuth 完了後に
# primary を openai-codex/gpt-5.3-codex に切り替え、gateway を再起動する。
# 用法: scp で VPS に送り、ssh で実行。例:
#   scp scripts/openclaw-vps/switch-to-gpt53codex.sh anicca@46.225.70.241:~/
#   ssh anicca@46.225.70.241 'bash ~/switch-to-gpt53codex.sh'
set -euo pipefail

STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
AUTH_PROFILES="$STATE_DIR/agents/anicca/agent/auth-profiles.json"
MODEL_ID="openai-codex/gpt-5.3-codex"

echo "=== 1) OAuth 確認 ==="
if [[ ! -f "$AUTH_PROFILES" ]]; then
  echo "NG: $AUTH_PROFILES がありません。先に OAuth を完了してください:"
  echo "  ssh -tt anicca@46.225.70.241 'openclaw models auth login --provider openai-codex'"
  exit 1
fi
if ! grep -q 'openai-codex' "$AUTH_PROFILES"; then
  echo "NG: auth-profiles.json に openai-codex が含まれていません。OAuth を完了してください。"
  exit 1
fi
echo "OK: openai-codex が確認できました。"

echo ""
echo "=== 2) gateway 一時停止 ==="
systemctl --user stop openclaw-gateway.service 2>/dev/null || true
sleep 2
echo "OK"

echo ""
echo "=== 3) allowlist + primary 設定 ==="
openclaw config set "agents.defaults.models.\"$MODEL_ID\"" '{"alias":"gpt53codex"}'
openclaw config set agents.defaults.model.primary "$MODEL_ID"
echo "primary = $(openclaw config get agents.defaults.model.primary)"
echo "OK"

echo ""
echo "=== 4) gateway 起動 ==="
systemctl --user start openclaw-gateway.service
sleep 5

echo ""
echo "=== 5) ログ確認（agent model） ==="
if journalctl --user -u openclaw-gateway.service -n 80 --no-pager | grep -q "agent model: $MODEL_ID"; then
  echo "OK: ログに 'agent model: $MODEL_ID' を確認しました。"
else
  echo "WARN: ログに 'agent model: $MODEL_ID' がまだ出ていません。"
  echo "直近ログ:"
  journalctl --user -u openclaw-gateway.service -n 30 --no-pager || true
  exit 1
fi

echo ""
echo "=== 完了 ==="
echo "Slack で @Anicca に1回メンションして、返信が1回だけかつモデルが $MODEL_ID であることを確認してください。"
