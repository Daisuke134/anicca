#!/usr/bin/env bash
# phase-prelaunch-content-daily.sh — daily countdown content for cafe launch
# cron: `0 12 * * *` JST (5/7 - 5/31 daily)
# Output: TT slideshow + IG post + X thread, "Day N before launch" countdown
set -uo pipefail

SKILL=~/.openclaw/skills/opening-cafe-tokyo-skills
CONFIG="$SKILL/data/config.json"
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
[ -f ~/anicca-monk-factory/.env ] && set -a && source ~/anicca-monk-factory/.env && set +a

LAUNCH_DATE="2026-06-01"
TODAY=$(date +%Y-%m-%d)
DAYS_TO_LAUNCH=$(( ($(date -j -f "%Y-%m-%d" "$LAUNCH_DATE" +%s) - $(date +%s)) / 86400 ))

if [ "$DAYS_TO_LAUNCH" -le 0 ]; then
  echo "▶ Launch day or after — switching to phase10-cross-post-daily.sh"
  exit 0
fi

echo "▶ phase-prelaunch-content  $TODAY  Days to launch: $DAYS_TO_LAUNCH"

PRODUCT_NAME=$(jq -r '.product.name' "$CONFIG")
PRICE=$(jq -r '.product.price_jpy' "$CONFIG")

mkdir -p "$SKILL/data/prelaunch"
QUEUE_FILE="$SKILL/data/prelaunch/content-queue.json"

# Compose post content
POST_TEXT_EN="Day $DAYS_TO_LAUNCH before launch.

$PRODUCT_NAME — cold-pressed mango juice, ¥$PRICE / 350ml, Tokyo-only delivery via Uber Eats.

Joining a waitlist? aniccaai.com/cafe

Run by Anicca, an autonomous Buddhist AI entity. 10% of every cup's profit → 10 humans on basic income.

#AniccaCafe #UberEatsTokyo #MangoJuice #BuddhistAI"

POST_TEXT_JP="ローンチまであと $DAYS_TO_LAUNCH 日。

$PRODUCT_NAME — コールドプレス マンゴージュース ¥$PRICE / 350ml、東京限定 Uber Eats デリバリー。

waitlist 登録: aniccaai.com/cafe

仏教 AI Anicca が運営、利益の 10% は 10 人のベーシックインカムへ。

#アニッカカフェ #UberEats東京 #マンゴージュース"

# Save to queue (for later cron firing or manual review)
jq -n --arg date "$TODAY" --argjson days "$DAYS_TO_LAUNCH" \
  --arg en "$POST_TEXT_EN" --arg jp "$POST_TEXT_JP" \
  '$ARGS.named' >> "$QUEUE_FILE"

echo "  EN ($DAYS_TO_LAUNCH days): $(echo "$POST_TEXT_EN" | head -1)"
echo "  JP ($DAYS_TO_LAUNCH days): $(echo "$POST_TEXT_JP" | head -1)"

# Post to X via Postiz (Anicca's main account)
POSTIZ_BASE_URL="${POSTIZ_BASE_URL:-https://app.postiz.com}"
X_INTEGRATION_ID="${POSTIZ_X_INTEGRATION_ID:-${POSTIZ_X_INTEGRATION:-}}"
if [ -n "${POSTIZ_API_KEY:-}" ] && [ -n "$X_INTEGRATION_ID" ]; then
  python3 - "$X_INTEGRATION_ID" "$POST_TEXT_EN" "$POSTIZ_BASE_URL" <<'PY' 2>&1 | head -3 || echo "  postiz x err"
import json, os, sys, urllib.request
integration_id, text, base_url = sys.argv[1:4]
body = json.dumps({
    "type": "draft",
    "shortLink": False,
    "posts": [{"integration": {"id": integration_id}, "value": [{"content": text, "media": []}]}],
}).encode()
req = urllib.request.Request(
    base_url.rstrip('/') + "/public/v1/posts",
    data=body,
    headers={"Authorization": f"Bearer {os.environ['POSTIZ_API_KEY']}", "Content-Type": "application/json"},
    method="POST",
)
try:
    resp = urllib.request.urlopen(req, timeout=20)
    print(resp.read().decode('utf-8', 'ignore')[:400])
except Exception as e:
    print(json.dumps({"error": str(e)[:200]}))
PY
fi

# TODO: Postiz IG (POSTIZ_EN_IG_INTEGRATION + POSTIZ_JP_IG_INTEGRATION)
# TODO: Postiz TT (POSTIZ_EN_TIKTOK_INTEGRATION + POSTIZ_JP_TIKTOK_INTEGRATION)
# TODO: Use product photos from data/cafe/product-photos/ (when fal.ai re-funded)

if command -v openclaw &>/dev/null; then
  openclaw message send --channel slack --target "${SLACK_CHANNEL:-{{profile.channels.reportChannel}}}" \
    --message "🍹 prelaunch content posted: $DAYS_TO_LAUNCH days to launch" 2>/dev/null || true
fi

echo "✓ phase-prelaunch-content done"
