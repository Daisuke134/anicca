#!/usr/bin/env bash
# VPS の Control UI に localhost 経由でアクセスするための SSH トンネル
# 使い方: このスクリプトを実行したままにしておく（別ターミナルで）
#         その後ブラウザで http://127.0.0.1:18789/ を開く

set -e
VPS_HOST="${OPENCLAW_VPS_HOST:-anicca@46.225.70.241}"
LOCAL_PORT=18789
REMOTE_PORT=18789

echo "SSH トンネルを起動します（このターミナルは閉じないでください）"
echo "  $LOCAL_PORT → $VPS_HOST:$REMOTE_PORT"
echo ""
echo "ブラウザで http://127.0.0.1:18789/ を開いてください"
echo "終了するには Ctrl+C"
echo ""

exec ssh -N -L "${LOCAL_PORT}:127.0.0.1:${REMOTE_PORT}" "$VPS_HOST"
