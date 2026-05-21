#!/usr/bin/env bash
# VPS 上で実行。セッションストアロック (sessions.json.lock) を解除して gateway を再起動する。
# 用法: scp してから ssh で実行
#   scp scripts/openclaw-vps/vps-fix-session-lock.sh anicca@46.225.70.241:~/
#   ssh anicca@46.225.70.241 'bash ~/vps-fix-session-lock.sh'
set -euo pipefail

SESSION_DIR="/home/anicca/.openclaw/agents/anicca/sessions"
LOCK_FILE="${SESSION_DIR}/sessions.json.lock"

echo "=== 1) gateway 停止 ==="
systemctl --user stop openclaw-gateway.service 2>/dev/null || true
sleep 2

echo "=== 2) 残プロセス kill ==="
pkill -9 -f openclaw-gateway 2>/dev/null || true
pkill -9 -x openclaw 2>/dev/null || true
sleep 1

echo "=== 3) ロックファイル削除 ==="
if [ -f "$LOCK_FILE" ]; then
  rm -f "$LOCK_FILE"
  echo "Removed: $LOCK_FILE"
else
  echo "No lock file found (already clean)."
fi

echo "=== 4) sessions ディレクトリ確認 ==="
ls -la "$SESSION_DIR" 2>/dev/null || echo "Directory missing: $SESSION_DIR"

echo "=== 5) gateway 再起動 ==="
systemctl --user start openclaw-gateway.service
sleep 2
systemctl --user status openclaw-gateway.service --no-pager || true

echo ""
echo "=== 完了 ==="
echo "Control UI を再読み込みして session が開けるか確認してください。"
