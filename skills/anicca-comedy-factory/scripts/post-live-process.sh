#!/usr/bin/env bash
# comedy-post-live-process — event-driven (Dais が録画 upload した時)
#
# Usage: post-live-process.sh <video_path> [city] [date]
#
# Flow:
#   1. ffmpeg で 9:16 1080x1920 (TikTok 規格)
#   2. data/skit-scripts/<today>-en.json から caption pull
#   3. Postiz upload-file → @anicca.comedy TikTok 投稿
#   4. live-events JSON に recording state 永続化 (city/date supplied 時)
#   5. Slack #metrics 報告
#
# 入力 (video_path) が無ければ silent exit 0 (cron 空回り OK)。
#
# stdout last line: ✅ post-live-process: postId=<id>

set -euo pipefail

VIDEO="${1:-}"
CITY="${2:-}"
DATE="${3:-}"

if [ -z "$VIDEO" ] || [ ! -f "$VIDEO" ]; then
  echo "⏳ post-live-process: no video provided, skipping (cron noop)"
  exit 0
fi

SKILL_DIR="$HOME/.openclaw/skills/anicca-comedy-factory"
DATA_DIR="$SKILL_DIR/data"
RECORDINGS="$DATA_DIR/recordings"
mkdir -p "$RECORDINGS"

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
: "${POSTIZ_API_KEY:?POSTIZ_API_KEY missing}"
: "${POSTIZ_TIKTOK_INTEGRATION_ID:?POSTIZ_TIKTOK_INTEGRATION_ID missing}"

source "$HOME/.openclaw/skills/sao-content-factory/lib/slack.sh"

TS=$(date +%Y%m%d-%H%M%S)
OUT="$RECORDINGS/${TS}.mp4"

ffmpeg -y -i "$VIDEO" \
  -vf "scale=w=1080:h=1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black" \
  -c:v libx264 -preset fast -crf 22 -c:a aac -b:a 128k \
  "$OUT" 2>/dev/null

if [ ! -s "$OUT" ]; then
  echo "❌ post-live-process: ffmpeg failed"
  exit 1
fi

TODAY=$(date +%Y-%m-%d)
CAPTION_FILE="$DATA_DIR/skit-scripts/${TODAY}-en.json"
if [ -f "$CAPTION_FILE" ]; then
  CAPTION=$(jq -r '.caption // .skit // ""' "$CAPTION_FILE" 2>/dev/null | head -c 280)
else
  CAPTION="impermanence is funny."
fi

UPLOAD=$(curl -sS -X POST "https://api.postiz.com/public/v1/uploads/upload-file" \
  -H "Authorization: $POSTIZ_API_KEY" \
  -F "file=@$OUT" 2>/dev/null || echo '{}')
MEDIA_PATH=$(echo "$UPLOAD" | jq -r '.path // .url // empty')

if [ -z "$MEDIA_PATH" ]; then
  echo "❌ post-live-process: postiz upload failed: $UPLOAD"
  exit 1
fi

POST_PAYLOAD=$(jq -n \
  --arg date "$(date -u +%Y-%m-%dT%H:%M:%S.000Z)" \
  --arg iid "$POSTIZ_TIKTOK_INTEGRATION_ID" \
  --arg cap "$CAPTION" --arg media "$MEDIA_PATH" \
  '{
    type: "now", date: $date,
    posts: [{
      integration: {id: $iid},
      settings: {__type: "tiktok", privacy_level: "PUBLIC_TO_EVERYONE"},
      value: [{content: $cap, image: [{path: $media}]}]
    }]
  }')

POST_RESP=$(curl -sS -X POST "https://api.postiz.com/public/v1/posts" \
  -H "Authorization: $POSTIZ_API_KEY" -H "Content-Type: application/json" \
  --data "$POST_PAYLOAD" 2>/dev/null || echo '[]')
POST_ID=$(echo "$POST_RESP" | jq -r '.[0].postId // empty')

if [ -z "$POST_ID" ]; then
  echo "❌ post-live-process: postiz post failed: $POST_RESP"
  exit 1
fi

if [ -n "$CITY" ] && [ -n "$DATE" ]; then
  EVT_FILE="$DATA_DIR/live-events/${CITY}-${DATE}.json"
  if [ -f "$EVT_FILE" ]; then
    tmp=$(mktemp)
    jq --arg path "$OUT" --arg pid "$POST_ID" --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
      '. += {recording_processed: {path: $path, tiktok_post_id: $pid, processed_at: $ts}}' \
      "$EVT_FILE" > "$tmp" && mv "$tmp" "$EVT_FILE"
  fi
fi

slack_metrics "*comedy-post-live-process:* TikTok 投稿 postId=$POST_ID / video=$OUT" >/dev/null || true
echo "✅ post-live-process: postId=$POST_ID"
