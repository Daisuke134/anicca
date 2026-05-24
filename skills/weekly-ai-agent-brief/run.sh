#!/usr/bin/env bash
# weekly-ai-agent-brief — weekly synthesis of 7-day AI agent intel for Dais
# - Reads last 7 days of: latest-papers + dais-x-feed-digest + mufg-epoc-watcher
# - 1 Grok synthesis call → produces (a) A4 brief.md (b) Marp slides.md
# - Posts both to Slack #metrics
#
# Idempotent: re-running on same date overwrites .md files + posts new Slack messages.

set -euo pipefail

SKILL_DIR="$HOME/.openclaw/skills/weekly-ai-agent-brief"
WORK_DIR="$HOME/.openclaw/workspace/weekly-ai-agent-brief"
DATE_JST="$(TZ=Asia/Tokyo date +%Y-%m-%d)"
TIME_JST="$(TZ=Asia/Tokyo date +%H:%M)"
BRIEF_OUT="$WORK_DIR/brief_${DATE_JST}.md"
SLIDES_OUT="$WORK_DIR/slides_${DATE_JST}.md"
RAW_OUT="$WORK_DIR/raw_${DATE_JST}.json"
RESP_OUT="$WORK_DIR/grok_response_${DATE_JST}.json"

mkdir -p "$WORK_DIR"

# Load env
if [ -f "$HOME/.openclaw/.env" ]; then
  set -a; . "$HOME/.openclaw/.env"; set +a
fi

: "${XAI_API_KEY:?XAI_API_KEY missing}"
: "${SLACK_BOT_TOKEN:?SLACK_BOT_TOKEN missing}"
SLACK_CHANNEL="${SLACK_CHANNEL_ID:-{{profile.channels.reportChannel}}}"

# Build prompt + call Grok in Python (robust against backticks/$ in JSON data)
python3 "$SKILL_DIR/build_and_call.py" \
  --date "$DATE_JST" \
  --xai-key "$XAI_API_KEY" \
  --brief-out "$BRIEF_OUT" \
  --slides-out "$SLIDES_OUT" \
  --raw-out "$RAW_OUT" \
  --resp-out "$RESP_OUT"

if [ ! -s "$BRIEF_OUT" ]; then
  echo "[run.sh] ERROR: brief.md empty"
  err_msg="📊 [Weekly AI Agent Brief] ${DATE_JST} ERROR: brief empty. See ${RESP_OUT}"
  curl -sS -X POST "https://slack.com/api/chat.postMessage" \
    -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
    -H "Content-type: application/json; charset=utf-8" \
    -d "$(jq -n --arg ch "$SLACK_CHANNEL" --arg t "$err_msg" '{channel:$ch, text:$t, mrkdwn:true}')" \
    | jq -r '"slack-post: ok=\(.ok)"'
  exit 1
fi

# Post brief.md to Slack
BRIEF_BODY=$(cat "$BRIEF_OUT")
SLACK_BRIEF=$(printf '📊 [Weekly AI Agent Brief] %s %s JST\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n_Past 7 days synthesis. ICLR 2026 Sao Paulo / MUIT 勉強会 / Anicca implementation の 3 用途。_\n\n%s' "$DATE_JST" "$TIME_JST" "$BRIEF_BODY")
SLACK_BRIEF_TRUNC=$(printf '%s' "$SLACK_BRIEF" | head -c 38000)

curl -sS -X POST "https://slack.com/api/chat.postMessage" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-type: application/json; charset=utf-8" \
  -d "$(jq -n --arg ch "$SLACK_CHANNEL" --arg t "$SLACK_BRIEF_TRUNC" '{channel:$ch, text:$t, mrkdwn:true, unfurl_links:false, unfurl_media:false}')" \
  | jq -r '"slack-post brief: ok=\(.ok) ts=\(.ts // "")"'

# Post slides.md to Slack
SLIDES_BODY=$(cat "$SLIDES_OUT")
SLACK_SLIDES=$(printf '📑 [Weekly AI Agent Brief — Slides Outline] %s\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n_Marp markdown。コピペして本人 30 分で finalize。_\n\n```\n%s\n```' "$DATE_JST" "$SLIDES_BODY")
SLACK_SLIDES_TRUNC=$(printf '%s' "$SLACK_SLIDES" | head -c 38000)

curl -sS -X POST "https://slack.com/api/chat.postMessage" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-type: application/json; charset=utf-8" \
  -d "$(jq -n --arg ch "$SLACK_CHANNEL" --arg t "$SLACK_SLIDES_TRUNC" '{channel:$ch, text:$t, mrkdwn:true, unfurl_links:false, unfurl_media:false}')" \
  | jq -r '"slack-post slides: ok=\(.ok) ts=\(.ts // "")"'

echo "[run.sh] done. brief=$BRIEF_OUT slides=$SLIDES_OUT"
