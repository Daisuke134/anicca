# 1.6.2 最終仕上げ 実行コマンド完全版（そのまま実行）

このファイルの目的は **1.6.2 を完全完了** させること。
中途報告禁止。**全部終わるまで戻るな**。

## 完了条件（全て必須）
- Railway 本番 API で以下が **HTTP 200**
  - `POST /api/ops/heartbeat`
  - `POST /api/admin/jobs/autonomy-check`
  - `POST /api/admin/jobs/moltbook-poster`（dry_run）
- ops/admin/services テストが全PASS
- TODO-NEXT を事実ベースで更新し、未完 `- [ ]` が 0
- 証跡ファイルを更新

---

## 0) 作業開始
```bash
set -euo pipefail
cd /Users/cbns03/Downloads/anicca-project

git checkout dev
git pull --ff-only

echo "branch=$(git branch --show-current)"
echo "head=$(git rev-parse --short HEAD)"
```

---

## 1) 必須 env を読み込む（ローカル）
```bash
set -a
[ -f /Users/cbns03/Downloads/anicca-project/.env ] && source /Users/cbns03/Downloads/anicca-project/.env
[ -f /Users/cbns03/.config/env/global.env ] && source /Users/cbns03/.config/env/global.env
set +a

for k in API_BASE_URL ANICCA_AGENT_TOKEN INTERNAL_API_TOKEN APIFY_API_TOKEN TWITTERAPI_KEY REDDAPI_API_KEY MOLTBOOK_BASE_URL MOLTBOOK_ACCESS_TOKEN; do
  if [ -n "${!k:-}" ]; then
    echo "OK:$k"
  else
    echo "MISSING:$k"
    exit 1
  fi
done
```

---

## 2) VPS に env 同期 + Gateway 再起動
```bash
cd /Users/cbns03/Downloads/anicca-project
bash scripts/openclaw-vps/sync-env-to-vps.sh

ssh anicca@46.225.70.241 'set -e; systemctl --user daemon-reload; systemctl --user restart openclaw-gateway.service; systemctl --user status openclaw-gateway.service --no-pager | sed -n "1,25p"'
```

---

## 3) ローカルテスト（必須）
```bash
cd /Users/cbns03/Downloads/anicca-project/apps/api
npx vitest run src/routes/ops src/routes/admin src/services/ops src/middleware/__tests__/opsAuth.test.js
```

---

## 4) Railway へ API を再デプロイ（ops/admin 最新反映）
> Railway CLI が未ログインなら先に `railway login`。

```bash
cd /Users/cbns03/Downloads/anicca-project/apps/api
railway up --ci
```

デプロイ完了待ち（成功になるまで確認）:
```bash
cd /Users/cbns03/Downloads/anicca-project/apps/api
railway status || true
```

---

## 5) 本番 API 疎通ゲート（3つすべて 200 必須）
```bash
set -euo pipefail

HB_CODE=$(curl -sS -o /tmp/hb.json -w '%{http_code}' \
  -X POST "${API_BASE_URL}/api/ops/heartbeat" \
  -H "Authorization: Bearer ${ANICCA_AGENT_TOKEN}" \
  -H 'Content-Type: application/json' \
  -d '{}')

echo "heartbeat_code=${HB_CODE}"
cat /tmp/hb.json; echo
[ "${HB_CODE}" = "200" ]

AUTO_CODE=$(curl -sS -o /tmp/auto.json -w '%{http_code}' \
  -X POST "${API_BASE_URL}/api/admin/jobs/autonomy-check" \
  -H "Authorization: Bearer ${INTERNAL_API_TOKEN}" \
  -H 'Content-Type: application/json' \
  -d '{"dry_run":true}')

echo "autonomy_code=${AUTO_CODE}"
cat /tmp/auto.json; echo
[ "${AUTO_CODE}" = "200" ]

MB_CODE=$(curl -sS -o /tmp/mb.json -w '%{http_code}' \
  -X POST "${API_BASE_URL}/api/admin/jobs/moltbook-poster" \
  -H "Authorization: Bearer ${INTERNAL_API_TOKEN}" \
  -H 'Content-Type: application/json' \
  -d '{"dry_run":true}')

echo "moltbook_code=${MB_CODE}"
cat /tmp/mb.json; echo
[ "${MB_CODE}" = "200" ]
```

---

## 6) VPS 側の配置・ジョブ数チェック
```bash
ssh anicca@46.225.70.241 'set -e; find ~/.openclaw/skills -name SKILL.md | wc -l; jq length ~/.openclaw/cron/jobs.json'
```

---

## 7) TODO-NEXT と証跡を更新
更新対象:
- `/Users/cbns03/Downloads/anicca-project/.cursor/plans/ios/1.6.2/implementation/TODO-NEXT-2026-02-09.md`
- `/Users/cbns03/Downloads/anicca-project/.cursor/plans/ios/1.6.2/implementation/DEPLOY-EVIDENCE-2026-02-11.md`

必須ルール:
- 推測で `[x]` にしない
- 200 / PASS / 実行ログがあるものだけ `[x]`
- 1行で証跡（HTTPコード or コマンド結果）を書く

---

## 8) 未完が0か機械判定（0でなければ失敗）
```bash
cd /Users/cbns03/Downloads/anicca-project

echo '--- TODO unchecked lines ---'
rg -n "^- \[ \]" .cursor/plans/ios/1.6.2/implementation/TODO-NEXT-2026-02-09.md || true

UNCHECKED_COUNT=$(rg -n "^- \[ \]" .cursor/plans/ios/1.6.2/implementation/TODO-NEXT-2026-02-09.md | wc -l | tr -d ' ')
echo "unchecked=${UNCHECKED_COUNT}"
[ "${UNCHECKED_COUNT}" = "0" ]
```

---

## 9) コミットして push
```bash
cd /Users/cbns03/Downloads/anicca-project

git add .cursor/plans/ios/1.6.2/implementation/TODO-NEXT-2026-02-09.md \
        .cursor/plans/ios/1.6.2/implementation/DEPLOY-EVIDENCE-2026-02-11.md \
        .cursor/plans/ios/1.6.2/implementation/AGENT-RUNBOOK-FINAL-1.6.2.md || true

git add apps/api/src/routes/ops/heartbeat.js apps/api/src/routes/ops/index.js apps/api/src/routes/admin || true

git commit -m "chore(1.6.2): close final ops/deploy gates and update SSOT evidence" || true
git push origin dev
```

---

## 10) 最終報告フォーマット（この形で返す）
- branch / commit
- 3エンドポイントHTTPコード（heartbeat/autonomy-check/moltbook-poster）
- vitest結果（何 files / 何 tests）
- TODO 未完数（`unchecked=0` 必須）
- 更新ファイル一覧
- 残課題（あれば具体名）

