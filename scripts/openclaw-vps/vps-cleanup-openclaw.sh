#!/usr/bin/env bash
# VPS 上で実行する。openclaw まわりを止めてクリーンにする。
# 用法: VPS にログインしてから bash で実行。
#   ssh anicca@46.225.70.241
#   bash (このファイルの内容を貼り付けるか、scp して実行)
set -euo pipefail

echo "=== 1) 今の openclaw まわりのプロセス ==="
ps aux | grep -E 'openclaw|node.*openclaw' | grep -v grep || true

echo ""
echo "=== 2) gateway を止める ==="
systemctl --user stop openclaw-gateway.service 2>/dev/null || true
sleep 2

echo ""
echo "=== 3) 残っている openclaw / node を kill ==="
pkill -9 -f openclaw-gateway 2>/dev/null || true
pkill -9 -x openclaw 2>/dev/null || true
# Node で openclaw を動かしている場合
pkill -9 -f 'node.*openclaw' 2>/dev/null || true
sleep 2

echo ""
echo "=== 4) まだ残っていないか確認 ==="
ps aux | grep -E 'openclaw|node.*openclaw' | grep -v grep || echo "OK: openclaw プロセスなし"

echo ""
echo "=== 5) 負荷・メモリ ==="
uptime
free -m 2>/dev/null || true

echo ""
echo "=== 完了 ==="
echo "gateway は止まった状態です。OAuth や切替スクリプトをやるときは、このあと必要に応じて start してください。"
