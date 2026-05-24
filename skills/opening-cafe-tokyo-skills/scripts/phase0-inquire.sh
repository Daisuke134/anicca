#!/usr/bin/env bash
# phase0-inquire.sh — send inquiry to a candidate kitchen
# Usage: bash phase0-inquire.sh <platform> <room_id|date>
#   platform = kashispace | theghostrestaurant | spacemarket
#   room_id  = numeric for kashispace; for theghostrestaurant pass YYYY-MM-DD viewing date
#
# Idempotency: data/cafe/inquiries/<platform>-<id>.json 既存なら skip (FORCE=true で上書き)
set -uo pipefail

PLATFORM="${1:?usage: $0 <platform> <room_id|date>}"
ID="${2:?}"
SKILL=~/.openclaw/skills/opening-cafe-tokyo-skills
CONFIG="${CONFIG:-$SKILL/data/config.json}"
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

mkdir -p "$SKILL/data/cafe/inquiries"
STATE_FILE="$SKILL/data/cafe/inquiries/$PLATFORM-$ID.json"

if [ -f "$STATE_FILE" ] && [ "${FORCE:-false}" != "true" ]; then
  EXISTING=$(jq -r '.gcal_event_id // empty' "$STATE_FILE")
  if [ -n "$EXISTING" ]; then
    echo "▶ already done: gcal=$EXISTING (FORCE=true to re-run)"
    exit 0
  fi
fi

# ── Compose inquiry message from config + product ───────────────────────────
PRODUCT_NAME=$(jq -r '.product.name' "$CONFIG")
PRODUCT_DESC=$(jq -r '.product.description' "$CONFIG")
HOME_STATION=$(jq -r '.operator.home_station' "$CONFIG")
WEEKLY_HOURS=$(jq -r '.preferences.weekly_hours' "$CONFIG")
WEEKLY_HRS_RANGE="${WEEKLY_HOURS}-$((WEEKLY_HOURS + 2))"

MSG_FILE=$(mktemp -t inquiry.XXXX.txt)
trap "rm -f $MSG_FILE" EXIT

cat > "$MSG_FILE" <<EOF
新規開業を検討しております、${PRODUCT_NAME} を ${HOME_STATION}駅エリアから配送する
ゴーストキッチン (Uber Eats メイン) の運営者です。

利用想定:
- 週末 2 日 (土日) 各 4-5 時間 = 月 ${WEEKLY_HRS_RANGE} 時間 × 4 週
- 単独運営、客席不要、配送ピックアップのみ
- 居住地: ${HOME_STATION}駅
- 主商品: ${PRODUCT_NAME} (${PRODUCT_DESC})

確認させていただきたい点:
1. 月料金の概算 (上記利用パターンでの)
2. 営業許可証 (飲食店営業許可) の取得状況、Uber Eats merchant 申請の代替書類として使えるか
3. 内見可能日 (5/12 月曜 第一希望)
4. その他制約事項 (調理機器持込可否、衛生条件、保管スペース等)

ご返信いただけますと幸いです。
EOF

# ── Dispatch to platform module ──────────────────────────────────────────────
case "$PLATFORM" in
  kashispace)
    RESULT=$(bash "$SKILL/scripts/lib/kashispace.sh" "$ID" "$MSG_FILE" | tail -1)
    ;;
  theghostrestaurant)
    RESULT=$(bash "$SKILL/scripts/lib/theghostrestaurant.sh" "$ID" "10:00～12:00" "$MSG_FILE" | tail -1)
    ;;
  spacemarket)
    echo "  spacemarket requires Dais signup first (cookies persist after manual login)"
    RESULT=$(jq -n --arg platform spacemarket --arg id "$ID" --arg status "blocked_dais_signup_needed" '$ARGS.named')
    ;;
  *)
    echo "ERR: unknown platform '$PLATFORM'"
    exit 1
    ;;
esac

# ── Calendar add (1pm 2-hour viewing slot for the 内見) ─────────────────────
source "$SKILL/scripts/lib/dais-alert.sh" 2>/dev/null || true
GCAL_ID=""
case "$PLATFORM" in
  kashispace)
    GCAL_ID=$(alert_human \
      "🔑 [REQUESTED] kashispace #${ID} 内見" \
      "2026-05-12T13:00:00+09:00" "2026-05-12T15:00:00+09:00" \
      "kashispace #${ID} (詳細は Gmail で確認)" \
      "kashispace ID ${ID} 内見申込済 (5/6送信)。担当者から日程確定の連絡待ち。受付確認メールを ${DAIS_EMAIL:-} で確認してください。" 2>/dev/null || echo "")
    ;;
  theghostrestaurant)
    GCAL_ID=$(alert_human \
      "🔑 [REQUESTED] theghostrestaurant 内見" \
      "${ID}T10:00:00+09:00" "${ID}T12:00:00+09:00" \
      "東京都千代田区神田三崎町3-6-1BACHビル2F (水道橋徒歩5分)" \
      "theghostrestaurant.tokyo 内見申込済。担当者から日程確定の連絡待ち。" 2>/dev/null || echo "")
    ;;
esac

# ── Persist state ────────────────────────────────────────────────────────────
SUBMITTED_AT=$(date -u +%FT%TZ)
echo "$RESULT" | jq \
  --arg gcal_event_id "$GCAL_ID" \
  --arg submitted_at "$SUBMITTED_AT" \
  '. + {gcal_event_id: $gcal_event_id, submitted_at: $submitted_at}' > "$STATE_FILE"

echo "✓ inquiry saved → $STATE_FILE"
jq -r '"\(.platform) | status=\(.status) | gcal=\(.gcal_event_id)"' "$STATE_FILE"
