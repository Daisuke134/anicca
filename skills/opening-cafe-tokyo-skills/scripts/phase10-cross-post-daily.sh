#!/usr/bin/env bash
# phase10-cross-post-daily.sh — 売上 + 注文写真 → IG/TT/X cross-post
# cron: `0 16 * * *` JST
# 連携: anicca-x-marketing-skill (X channel) + reelclaw factory (TT/IG)
#
# Slack 報告 必須 (5/9 v27 fix — daily cron silent 解消)
#
# stdout final line:
#   ✅ phase10-cross-post: revenue=¥<N> orders=<N> (status) | slack ts=<ts>
#   ❌ phase10-cross-post FAILED: <reason>

set -uo pipefail

SKILL=~/.openclaw/skills/opening-cafe-tokyo-skills
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

PYTHON="python3"
TODAY=$(date +%Y-%m-%d)
SALES="$SKILL/data/cafe/sales/$TODAY.json"

slack_post() {
  local title="$1"; local fields_json="$2"; local extra="${3:-}"
  "$PYTHON" - "$SLACK_CHANNEL_ID" "$SLACK_BOT_TOKEN" "$title" "$fields_json" "$extra" <<'PY'
import sys, json, urllib.request
ch, token, title, fields_json, extra = sys.argv[1:6]
fields = json.loads(fields_json) if fields_json else []
blocks = [{"type":"header","text":{"type":"plain_text","text":title}}]
if fields:
    blocks.append({"type":"section","fields":fields})
if extra:
    blocks.append({"type":"section","text":{"type":"mrkdwn","text":extra}})
payload = {"channel": ch, "text": title, "blocks": blocks}
req = urllib.request.Request(
    "https://slack.com/api/chat.postMessage",
    data=json.dumps(payload).encode(),
    headers={"Authorization":f"Bearer {token}","Content-Type":"application/json; charset=utf-8"},
    method="POST")
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        print(json.loads(r.read().decode()).get("ts","?"))
except Exception:
    print("?")
PY
}

# === main ===
STATUS="ok"
REVENUE=0
ORDERS=0
NOTES=""

if [ ! -f "$SALES" ]; then
  STATUS="no_sales_file"
  NOTES="data/cafe/sales/$TODAY.json missing — Uber 承認後 sales scrape 開始時点で生成"
else
  REVENUE=$(jq -r '.revenue_jpy // 0' "$SALES")
  ORDERS=$(jq -r '.orders_count // 0' "$SALES")
  if [ "$REVENUE" -le 0 ]; then
    STATUS="zero_revenue_skip"
    NOTES="revenue=¥0 — pre-launch or no orders today"
  fi
fi

# Slack 報告 (毎日必ず投稿、status 含む)
FIELDS_JSON=$("$PYTHON" -c "
import json
print(json.dumps([
    {'type':'mrkdwn','text':f'*revenue:*\n¥${REVENUE}'},
    {'type':'mrkdwn','text':f'*orders:*\n${ORDERS}'},
    {'type':'mrkdwn','text':f'*status:*\n${STATUS}'},
    {'type':'mrkdwn','text':f'*date:*\n${TODAY}'},
]))")
EXTRA="${NOTES}"
TS=$(slack_post "🔄 cafe-cross-post-daily" "$FIELDS_JSON" "$EXTRA")

# 売上ある時のみ実 cross-post 実行 (本実装は launch 後 — 現状 stub + Slack のみ)
if [ "$STATUS" = "ok" ]; then
  echo "▶ phase10: cross-post $TODAY revenue=¥$REVENUE orders=$ORDERS (TODO: actual posting)"
fi

echo "✅ phase10-cross-post: revenue=¥${REVENUE} orders=${ORDERS} status=${STATUS} | slack ts=${TS}"
