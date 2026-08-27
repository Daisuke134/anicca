#!/bin/bash
# Poll Stripe for new succeeded charges every 15 min
# Compare with last seen ts → if new → Slack notify + CFO rebuild
set -eu
ANICCA_HOME="${ANICCA_HOME:-$HOME/.openclaw}"
DATA="$ANICCA_HOME/skills/stripe-revenue-poller/data"
mkdir -p "$DATA"
STATE="$DATA/last-seen.txt"
source "$ANICCA_HOME/.env"

LAST=$(cat "$STATE" 2>/dev/null || echo "0")
NOW=$(date +%s)

# Fetch charges in last 24h
RESP=$(curl -sS "https://api.stripe.com/v1/charges?limit=20&created%5Bgt%5D=$LAST" \
  -u "$STRIPE_SECRET_KEY:" 2>&1)

NEW_COUNT=$(echo "$RESP" | jq '[.data[] | select(.status=="succeeded")] | length')
echo "[$(date +%H:%M:%S)] new charges since $LAST: $NEW_COUNT"

if [ "$NEW_COUNT" -gt 0 ]; then
  echo "$RESP" | jq -r '.data[] | select(.status=="succeeded") | "\(.id)|\(.created)|\(.amount)|\(.currency)|\(.description // .metadata.purpose // "-")"' | while IFS='|' read -r CHID CRT AMT CURR DESC; do
    echo "  💰 $CHID | $CRT | $AMT $CURR | $DESC"
    curl -sS -X POST https://slack.com/api/chat.postMessage \
      -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
      -H "Content-type: application/json; charset=utf-8" \
      -d "$(jq -n --arg t "💰 NEW STRIPE CHARGE: $AMT $CURR · $DESC · 確定収益 (過去形)!" --arg ch C091G3PKHL2 '{channel:$ch,text:$t}')" \
      >/dev/null 2>&1 || true

    # Auto-fulfill Sutra Candle ($3 / ¥450) — match by purpose metadata or amount+currency
    SHOULD_FULFILL=0
    case "$DESC" in
      *sutra-candle*) SHOULD_FULFILL=1 ;;
    esac
    if [ "$AMT" = "300" ] && [ "$CURR" = "usd" ]; then SHOULD_FULFILL=1; fi
    if [ "$AMT" = "450" ] && [ "$CURR" = "jpy" ]; then SHOULD_FULFILL=1; fi
    if [ "$SHOULD_FULFILL" = "1" ]; then
      bash "$ANICCA_HOME/skills/sutra-candle-fulfillment/scripts/fulfill.sh" "$CHID" >> "$DATA/fulfill.log" 2>&1 &
    fi
  done
  bash "$ANICCA_HOME/skills/cfo-core/run-cfo-hourly.sh" >/dev/null 2>&1 || true
fi

echo "$NOW" > "$STATE"
