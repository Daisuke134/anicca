#!/usr/bin/env bash
# phase2-monitor-and-speak.sh — Monitor meeting transcript + (optionally) speak
# Usage: phase2-monitor-and-speak.sh <bot_id> [intro_text]
set -euo pipefail

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
SKILL=~/.openclaw/skills/anicca-meeting-attendant
source "$SKILL/scripts/lib/attendee.sh"

BOT_ID="${1:?bot_id required}"
INTRO="${2:-Hello everyone. I am Anicca, an autonomous AI entity attending on behalf of Anicca AI. Solidarity.}"

echo "▶ phase2  bot=$BOT_ID"

# Wait until bot is in meeting
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  STATE=$(attendee_get "$BOT_ID" | python3 -c "import sys,json;print(json.load(sys.stdin).get('state',''))")
  echo "  state[$i]: $STATE"
  case "$STATE" in
    joined|in_call|connected|active)
      break
      ;;
    failed_to_join|ended)
      echo "❌ bot exited: $STATE"
      exit 1
      ;;
  esac
  sleep 5
done

echo "▶ speaking intro"
attendee_speak "$BOT_ID" "$INTRO" | head -3
echo "✅ intro spoken"

# 続きは event-driven (transcript ストリーム → Claude → attendee_speak)
# 初回 MVP は intro のみ。Q&A はオペレーター手動 or 別 phase で連携

echo "✅ phase2: monitoring (passive, intro only)"
