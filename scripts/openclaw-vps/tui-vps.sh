#!/usr/bin/env bash
# OpenClaw TUI を VPS の Gateway に接続して起動する。
# 前提: ローカル 18789 が VPS への SSH トンネルになっていること。
#       トンネルがない場合は ./tunnel-control-ui.sh を別ターミナルで実行する。
#
# 用法: ./scripts/openclaw-vps/tui-vps.sh

set -e

VPS_HOST="${OPENCLAW_VPS_HOST:-anicca@46.225.70.241}"

# 18789 がトンネルか確認（ssh が LISTEN ならトンネル）
if ! lsof -i :18789 2>/dev/null | grep -q "ssh.*LISTEN"; then
  if lsof -i :18789 2>/dev/null | grep -q "node.*LISTEN"; then
    echo "⚠️  ポート 18789 はローカルの OpenClaw gateway が使用中です。"
    echo "   VPS に繋ぐには gateway を止めてから、別ターミナルで:"
    echo "   ./scripts/openclaw-vps/tunnel-control-ui.sh"
    echo "   を実行し、このスクリプトを再度実行してください。"
    exit 1
  else
    echo "⚠️  ポート 18789 で何も動いていません。先に SSH トンネルを起動してください:"
    echo "   ./scripts/openclaw-vps/tunnel-control-ui.sh"
    exit 1
  fi
fi

TOKEN=$(ssh -o BatchMode=yes "$VPS_HOST" "python3 -c \"
import json, os
p = os.path.expanduser('~/.openclaw/openclaw.json')
with open(p) as f:
    d = json.load(f)
print(d.get('gateway', {}).get('auth', {}).get('token', ''))
\"" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "❌ VPS から gateway token の取得に失敗しました。ssh $VPS_HOST が通るか確認してください。"
  exit 1
fi

export OPENCLAW_GATEWAY_TOKEN="$TOKEN"
echo "✅ Gateway token 取得済み (length ${#TOKEN}). VPS に接続して TUI を起動します (ws://127.0.0.1:18789 → VPS)"
exec openclaw tui
