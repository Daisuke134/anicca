# VPS を一度止めてクリーンにする手順

**やること:** VPS に SSH して、openclaw まわりのプロセスを全部止める。

---

## やり方（2パターン）

### A) コマンドを直接叩く（推奨）

**1. VPS にログイン**
```bash
ssh anicca@46.225.70.241
```

**2. ログインしたら、以下を順に貼り付けて実行**

```bash
# gateway 停止
systemctl --user stop openclaw-gateway.service
sleep 2

# 残りを kill
pkill -9 -f openclaw-gateway 2>/dev/null || true
pkill -9 -x openclaw 2>/dev/null || true
pkill -9 -f 'node.*openclaw' 2>/dev/null || true
sleep 2

# 確認（何も出なければOK）
ps aux | grep -E 'openclaw|node.*openclaw' | grep -v grep || echo "OK: プロセスなし"
```

**3. 抜ける**
```bash
exit
```

---

### B) スクリプトを送って実行

**ローカルで（anicca-project のルートで）:**
```bash
scp scripts/openclaw-vps/vps-cleanup-openclaw.sh anicca@46.225.70.241:~/
ssh anicca@46.225.70.241 'bash ~/vps-cleanup-openclaw.sh'
```

---

## クリーンアップのあと

- gateway は止まったまま。
- GPT-5.3 Codex の手順（OAuth → 切替スクリプト）をやると、スクリプト内で `systemctl --user start openclaw-gateway.service` が走ってまた起動する。
- いったん負荷を下げたいだけなら、このクリーンアップだけでOK。
