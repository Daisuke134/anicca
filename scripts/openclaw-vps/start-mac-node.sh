#!/usr/bin/env bash
# Mac を OpenClaw Node として VPS Gateway に接続する
# 使用前: SSH トンネルを別ターミナルで起動しておく
#   ssh -N -L 18790:127.0.0.1:18789 anicca@100.73.121.4

set -e

VPS_HOST="${OPENCLAW_VPS_HOST:-anicca@46.225.70.241}"
LOCAL_PORT=18790

# トンネル確認
if ! pgrep -f "18790:127.0.0.1:18789" >/dev/null 2>&1; then
  echo "⚠️  SSH トンネルが起動していません。先に以下を実行してください:"
  echo "   ssh -N -L ${LOCAL_PORT}:127.0.0.1:18789 ${VPS_HOST}"
  exit 1
fi

# token 取得
TOKEN=$(ssh "$VPS_HOST" "python3 -c \"
import json, os
d = json.load(open(os.path.expanduser('~/.openclaw/openclaw.json')))
print(d.get('gateway', {}).get('auth', {}).get('token', ''))
\"")

if [ -z "$TOKEN" ]; then
  echo "❌ Gateway token の取得に失敗しました"
  exit 1
fi

export OPENCLAW_GATEWAY_TOKEN="$TOKEN"
echo "✅ Node を起動中... (Ctrl+C で終了)"
exec openclaw node run --host 127.0.0.1 --port "$LOCAL_PORT" --display-name "mac"
