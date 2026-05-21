# 1.6.2 VPS デプロイ最短版

**前提:** `VPS_HOST`, `VPS_USER` を環境変数で設定済み（例: `anicca@46.225.70.241`）

---

## 1. skills 同期

```bash
cd /path/to/anicca-project
rsync -av --exclude='jobs.json' openclaw-skills/ ${VPS_USER}@${VPS_HOST}:/home/anicca/.openclaw/skills/
```

## 2. jobs.json 反映（Gateway 停止必須）

```bash
ssh ${VPS_USER}@${VPS_HOST} 'systemctl --user stop openclaw-gateway.service 2>/dev/null || true'
scp openclaw-skills/jobs.json ${VPS_USER}@${VPS_HOST}:/home/anicca/.openclaw/cron/jobs.json
ssh ${VPS_USER}@${VPS_HOST} 'systemctl --user start openclaw-gateway.service'
```

## 3. env 確認（値は表示しない）

```bash
ssh ${VPS_USER}@${VPS_HOST} 'source ~/.openclaw/.env 2>/dev/null; for k in API_BASE_URL ANICCA_AGENT_TOKEN APIFY_API_TOKEN TWITTERAPI_KEY REDDAPI_API_KEY MOLTBOOK_BASE_URL MOLTBOOK_ACCESS_TOKEN; do [ -n "${!k}" ] && echo OK:$k || echo MISSING:$k; done'
```

## 4. gateway 再起動

```bash
ssh ${VPS_USER}@${VPS_HOST} 'systemctl --user restart openclaw-gateway.service || systemctl restart openclaw-gateway || pm2 restart openclaw-gateway || true'
```

## 5. heartbeat 疎通確認

```bash
ssh ${VPS_USER}@${VPS_HOST} 'source ~/.openclaw/.env 2>/dev/null; curl -sS -X POST "$API_BASE_URL/api/ops/heartbeat" -H "Authorization: Bearer $ANICCA_AGENT_TOKEN" -H "Content-Type: application/json" -d "{}"'
```

→ 200 系 + JSON body で ok: true 等を確認。
