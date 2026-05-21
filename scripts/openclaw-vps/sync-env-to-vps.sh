#!/usr/bin/env bash
# ローカル anicca-project/.env を VPS の .env 2 箇所に**完全上書き**同期する。
# 正は常にローカル .env のみ。VPS の ~/.openclaw/.env と ~/.env はこれと完全に同一になる。
# 使い方: プロジェクトルートで bash scripts/openclaw-vps/sync-env-to-vps.sh
# 前提: ssh anicca@46.225.70.241 が通ること。
# 確認: 同期後 md5 が一致することを推奨（ローカル md5 -q .env と VPS md5sum ~/.openclaw/.env）

set -e
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"
VPS_HOST="anicca@46.225.70.241"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Error: .env not found at $ENV_FILE"
  exit 1
fi

echo "Syncing .env to VPS (openclaw + home)..."
ssh "$VPS_HOST" "mkdir -p /home/anicca/.openclaw && cat > /home/anicca/.openclaw/.env" < "$ENV_FILE"
ssh "$VPS_HOST" "cat > /home/anicca/.env" < "$ENV_FILE"
echo "Ensuring moltbook-interact credentials from MOLTBOOK_ACCESS_TOKEN..."
ssh "$VPS_HOST" '
source /home/anicca/.openclaw/.env 2>/dev/null
if [[ -n "$MOLTBOOK_ACCESS_TOKEN" ]]; then
  mkdir -p /home/anicca/.config/moltbook
  echo "{\"api_key\":\"$MOLTBOOK_ACCESS_TOKEN\",\"agent_name\":\"Anicca\"}" > /home/anicca/.config/moltbook/credentials.json
  chmod 600 /home/anicca/.config/moltbook/credentials.json 2>/dev/null || true
  echo "  Created ~/.config/moltbook/credentials.json"
else
  echo "  MOLTBOOK_ACCESS_TOKEN not set; skip credentials.json"
fi
'
echo "Done. VPS paths: /home/anicca/.openclaw/.env, /home/anicca/.env"
