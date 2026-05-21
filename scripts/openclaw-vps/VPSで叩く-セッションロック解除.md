# セッションストアロック解除（timeout acquiring session store lock）

**症状:** Control UI（`http://127.0.0.1:18789/chat?session=agent%3Aanicca%3Amain`）で  
`Error: timeout acquiring session store lock: /home/anicca/.openclaw/agents/anicca/sessions/sessions.json.lock` と表示される。

**原因:** セッションストア（`sessions.json`）への排他アクセス用ロックファイルが、プロセスクラッシュなどで解放されず残っている。

---

## 対処（VPS で実行）

### A) コマンドを直接叩く（推奨）

**1. VPS にログイン**
```bash
ssh anicca@46.225.70.241
```

**2. 以下を順に実行**

```bash
# gateway 停止（ロックを握っているプロセスを止める）
systemctl --user stop openclaw-gateway.service
sleep 2

# 念のため残プロセスを kill
pkill -9 -f openclaw-gateway 2>/dev/null || true
pkill -9 -x openclaw 2>/dev/null || true
sleep 1

# ロックファイルのみ削除（sessions.json は触らない）
rm -f /home/anicca/.openclaw/agents/anicca/sessions/sessions.json.lock

# 確認
ls -la /home/anicca/.openclaw/agents/anicca/sessions/

# gateway 再起動
systemctl --user start openclaw-gateway.service
systemctl --user status openclaw-gateway.service --no-pager
```

**3. 抜ける**
```bash
exit
```

**4. ブラウザで Control UI を再読み込み**  
`http://127.0.0.1:18789/chat?session=agent%3Aanicca%3Amain` が開けるか確認。

---

### B) スクリプトで実行

**ローカル（anicca-project ルート）で:**
```bash
scp scripts/openclaw-vps/vps-fix-session-lock.sh anicca@46.225.70.241:~/
ssh anicca@46.225.70.241 'bash ~/vps-fix-session-lock.sh'
```

---

## 注意

| 項目 | 説明 |
|------|------|
| `sessions.json` | **削除しない**。会話履歴が入っている。 |
| `sessions.json.lock` | **削除してよい**。ロック用の一時ファイル。 |
| 再発 | クラッシュや強制終了で再度ロックが残ることがある。同じ手順で解除可能。 |
