#!/usr/bin/env bash
# status.sh — print full lifecycle status, suggest next action, post to Slack
set -uo pipefail

SKILL=~/.openclaw/skills/opening-cafe-tokyo-skills
CONFIG="$SKILL/data/config.json"
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

ENTITY=$(jq -r '.entity_name' "$CONFIG" 2>/dev/null || echo "?")
echo "▶ opening-cafe-tokyo-skills status — entity=$ENTITY"
echo

# Phase 0 — inquiries
echo "Phase 0: Kitchen discover + 内見申込"
if ls "$SKILL/data/cafe/inquiries"/*.json >/dev/null 2>&1; then
  for f in "$SKILL/data/cafe/inquiries"/*.json; do
    PLATFORM=$(jq -r '.platform // "?"' "$f")
    ID=$(jq -r '.room_id // .date // "?"' "$f")
    STATUS=$(jq -r '.status // "?"' "$f")
    echo "  - $PLATFORM #$ID: $STATUS"
  done
else
  echo "  (no inquiries yet)"
fi
echo

# Phase 1 — operator_id (開業届け)
echo "Phase 1: 個人事業主 開業届け"
if [ -f "$SKILL/data/cafe/operator_id.json" ]; then
  ID=$(jq -r '.kojin_number // empty' "$SKILL/data/cafe/operator_id.json")
  echo "  個人番号: ${ID:-pending}"
else
  echo "  (not started — depends on Phase 0 selection)"
fi
echo

# Phase 4 — Uber merchant
echo "Phase 4: Uber Eats merchant"
if [ -f "$SKILL/data/cafe/uber_signup.json" ]; then
  M=$(jq -r '.merchant_id // "pending"' "$SKILL/data/cafe/uber_signup.json")
  echo "  merchant_id: $M"
else
  echo "  (not started)"
fi
echo

# Phase 9 — daily ops
echo "Phase 9: Daily ops"
TODAY=$(date +%Y-%m-%d)
if [ -f "$SKILL/data/cafe/sales/$TODAY.json" ]; then
  R=$(jq -r '.revenue_jpy // 0' "$SKILL/data/cafe/sales/$TODAY.json")
  echo "  today revenue: ¥$R"
else
  echo "  (no sales sync today — pre-launch)"
fi
echo

# Slack 報告
if command -v openclaw &>/dev/null; then
  REPORT="🍱 opening-cafe-tokyo-skills weekly status (entity=$ENTITY)
Phase 0: $(ls "$SKILL/data/cafe/inquiries"/*.json 2>/dev/null | wc -l | tr -d ' ') inquiries sent
Phase 1: $([ -f "$SKILL/data/cafe/operator_id.json" ] && echo 'started' || echo 'pending')
Phase 4: $([ -f "$SKILL/data/cafe/uber_signup.json" ] && echo 'started' || echo 'pending')
Phase 9: $([ -f "$SKILL/data/cafe/sales/$TODAY.json" ] && echo 'live' || echo 'pre-launch')"
  openclaw message send --channel slack --target "${SLACK_CHANNEL:-{{profile.channels.reportChannel}}}" \
    --message "$REPORT" 2>/dev/null || true
fi
