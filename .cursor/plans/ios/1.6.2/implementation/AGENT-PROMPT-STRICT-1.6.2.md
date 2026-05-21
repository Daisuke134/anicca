# AGENT PROMPT (STRICT) - 1.6.2 完了まで戻るな

あなたのミッションは **1.6.2 を完了** させること。途中報告禁止。失敗時は原因を直して再実行。

## 作業ディレクトリ
`/Users/cbns03/Downloads/anicca-project`

## 正本
`/Users/cbns03/Downloads/anicca-project/.cursor/plans/ios/1.6.2/implementation/TODO-NEXT-2026-02-09.md`

## ゴール（全て必須）
1. `POST /api/ops/heartbeat` が 200
2. `POST /api/admin/jobs/autonomy-check` が 200
3. `POST /api/admin/jobs/moltbook-poster` (dry_run) が 200
4. ops/admin/services vitest が全PASS
5. TODO-NEXT の未完 `- [ ]` が 0
6. 証跡ファイル更新（HTTPコード、テスト結果、実行コマンド）

## 実行コマンド（この順番で必ず実行）
```bash
set -euo pipefail
cd /Users/cbns03/Downloads/anicca-project

git checkout dev
git pull --ff-only

set -a
[ -f .env ] && source .env
[ -f /Users/cbns03/.config/env/global.env ] && source /Users/cbns03/.config/env/global.env
set +a

for k in API_BASE_URL ANICCA_AGENT_TOKEN INTERNAL_API_TOKEN APIFY_API_TOKEN TWITTERAPI_KEY REDDAPI_API_KEY MOLTBOOK_BASE_URL MOLTBOOK_ACCESS_TOKEN; do
  [ -n "${!k:-}" ] || { echo "MISSING:$k"; exit 1; }
done

bash scripts/openclaw-vps/sync-env-to-vps.sh
ssh anicca@46.225.70.241 'set -e; systemctl --user restart openclaw-gateway.service'

cd apps/api
npx vitest run src/routes/ops src/routes/admin src/services/ops src/middleware/__tests__/opsAuth.test.js
railway up --ci

cd /Users/cbns03/Downloads/anicca-project
HB=$(curl -sS -o /tmp/hb.json -w '%{http_code}' -X POST "${API_BASE_URL}/api/ops/heartbeat" -H "Authorization: Bearer ${ANICCA_AGENT_TOKEN}" -H 'Content-Type: application/json' -d '{}')
AU=$(curl -sS -o /tmp/au.json -w '%{http_code}' -X POST "${API_BASE_URL}/api/admin/jobs/autonomy-check" -H "Authorization: Bearer ${INTERNAL_API_TOKEN}" -H 'Content-Type: application/json' -d '{"dry_run":true}')
MB=$(curl -sS -o /tmp/mb.json -w '%{http_code}' -X POST "${API_BASE_URL}/api/admin/jobs/moltbook-poster" -H "Authorization: Bearer ${INTERNAL_API_TOKEN}" -H 'Content-Type: application/json' -d '{"dry_run":true}')

echo "heartbeat=$HB autonomy=$AU moltbook=$MB"
cat /tmp/hb.json; echo
cat /tmp/au.json; echo
cat /tmp/mb.json; echo

[ "$HB" = "200" ]
[ "$AU" = "200" ]
[ "$MB" = "200" ]

UNCHECKED=$(rg -n "^- \[ \]" .cursor/plans/ios/1.6.2/implementation/TODO-NEXT-2026-02-09.md | wc -l | tr -d ' ')
echo "unchecked=$UNCHECKED"
[ "$UNCHECKED" = "0" ]
```

## 更新必須ファイル
- `.cursor/plans/ios/1.6.2/implementation/TODO-NEXT-2026-02-09.md`
- `.cursor/plans/ios/1.6.2/implementation/DEPLOY-EVIDENCE-2026-02-11.md`

## 最終報告フォーマット（この形だけ許可）
- branch / commit
- heartbeat/autonomy-check/moltbook-poster のHTTPコード
- vitest pass件数
- TODO unchecked件数（0以外は失敗）
- 変更ファイル一覧
- 残課題（なければ「なし」）
