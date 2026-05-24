#!/usr/bin/env bash
# anicca-webapp-x-marketing — Channel E: $50 promoted-post boost (monthly)
# Picks last-30-day winner thread by impressions and boosts via X Ads.
set -uo pipefail

SKILL=~/.openclaw/skills/anicca-webapp-x-marketing
DRY_RUN="${DRY_RUN:-false}"
BUDGET_USD="${BUDGET_USD:-50}"
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

echo "▶ promote — pick winner thread"

# Find last-30-day Channel B threads, sort by impressions (impressions field
# requires X Analytics enrichment; placeholder uses date order until x_analytics cron lands)
WINNER=$(ls -t "$SKILL/state/threads/" 2>/dev/null \
  | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}-painpoint-' \
  | head -1)

[ -z "$WINNER" ] && { echo "  no thread to promote"; exit 0; }

WINNER_FILE="$SKILL/state/threads/$WINNER"
APP=$(jq -r .app "$WINNER_FILE")
DATE=$(jq -r .date "$WINNER_FILE")
echo "  winner: $WINNER  app=$APP  date=$DATE"

# X Ads requires: paid X Premium + X Ads API credentials. Skill writes out
# the boost intent for now; manual boost via x.com/i/ads (Dais).
PROMO_FILE="$SKILL/state/winner-thread.json"
jq -n \
  --arg date "$DATE" --arg app "$APP" --arg thread_file "$WINNER" \
  --argjson budget_usd "$BUDGET_USD" \
  --arg status "$([ "$DRY_RUN" = "true" ] && echo "dry" || echo "promote_queued")" \
  --arg picked_at "$(date -u +%FT%TZ)" \
  '$ARGS.named' > "$PROMO_FILE"

if command -v openclaw &>/dev/null; then
  openclaw message send --channel slack --target "${SLACK_CHANNEL:-{{profile.channels.reportChannel}}}" \
    --text "💵 X promote winner: $APP @ $DATE budget=\$$BUDGET_USD — boost via x.com/i/ads/<post-id>" 2>/dev/null || true
fi

echo "✓ promote queued → $PROMO_FILE"
