#!/usr/bin/env bash
# comedy-tiktok-cross-post-daily — 16 JST 毎日
#
# Flow:
#   1. data/recordings/ から 24h 以内の最新 mp4 を選定
#   2. 既に cross-post 済 (data/cross-post-history.json) ならスキップ (idempotent)
#   3. Postiz で IG + X integration に同 video を投稿
#   4. data/cross-post-history.json に追加
#
# 録画が無ければ silent exit 0 (cron 空回り OK)。
#
# stdout last line: ✅ cross-post: <N> platforms / OR ⏳ cross-post: no recording

set -euo pipefail

SKILL_DIR="$HOME/.openclaw/skills/anicca-comedy-factory"
DATA_DIR="$SKILL_DIR/data"
RECORDINGS="$DATA_DIR/recordings"
HISTORY="$DATA_DIR/cross-post-history.json"

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
: "${POSTIZ_API_KEY:?POSTIZ_API_KEY missing}"
[ -f "$HISTORY" ] || echo '[]' > "$HISTORY"

LATEST=$(find "$RECORDINGS" -name "*.mp4" -mtime -1 2>/dev/null | sort | tail -1 || true)
if [ -z "$LATEST" ]; then
  echo "⏳ cross-post: no recording within 24h, skipping"
  exit 0
fi

if jq -e --arg p "$LATEST" '.[] | select(.path == $p)' "$HISTORY" >/dev/null 2>&1; then
  echo "⏳ cross-post: $LATEST already cross-posted"
  exit 0
fi

source "$HOME/.openclaw/skills/sao-content-factory/lib/slack.sh"

IG_INTEGRATION="${POSTIZ_IG_INTEGRATION_ID:-}"
X_INTEGRATION="${POSTIZ_X_INTEGRATION_ID:-}"

TODAY=$(date +%Y-%m-%d)
CAPTION_FILE="$DATA_DIR/skit-scripts/${TODAY}-en.json"
if [ -f "$CAPTION_FILE" ]; then
  CAPTION=$(jq -r '.caption // .skit // ""' "$CAPTION_FILE" 2>/dev/null | head -c 270)
else
  CAPTION="impermanence is funny."
fi

UPLOAD=$(curl -sS -X POST "https://api.postiz.com/public/v1/uploads/upload-file" \
  -H "Authorization: $POSTIZ_API_KEY" \
  -F "file=@$LATEST" 2>/dev/null || echo '{}')
MEDIA_PATH=$(echo "$UPLOAD" | jq -r '.path // .url // empty')

if [ -z "$MEDIA_PATH" ]; then
  echo "❌ cross-post: upload failed"
  exit 1
fi

posted=0
post_ids=""
for pair in "ig:$IG_INTEGRATION" "x:$X_INTEGRATION"; do
  platform="${pair%:*}"
  iid="${pair#*:}"
  [ -z "$iid" ] && continue
  ttype="$platform"
  [ "$platform" = "ig" ] && ttype="instagram"

  payload=$(jq -n \
    --arg date "$(date -u +%Y-%m-%dT%H:%M:%S.000Z)" \
    --arg iid "$iid" --arg ttype "$ttype" --arg cap "$CAPTION" --arg media "$MEDIA_PATH" \
    '{type: "now", date: $date,
      posts: [{integration: {id: $iid}, settings: {__type: $ttype},
        value: [{content: $cap, image: [{path: $media}]}]}]}')

  resp=$(curl -sS -X POST "https://api.postiz.com/public/v1/posts" \
    -H "Authorization: $POSTIZ_API_KEY" -H "Content-Type: application/json" \
    --data "$payload" 2>/dev/null || echo '[]')
  pid=$(echo "$resp" | jq -r '.[0].postId // empty')
  if [ -n "$pid" ]; then
    posted=$((posted + 1))
    post_ids="${post_ids}${platform}=${pid} "
  fi
done

tmp=$(mktemp)
jq --arg path "$LATEST" --arg ids "$post_ids" --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '. += [{path: $path, post_ids: $ids, posted_at: $ts}]' "$HISTORY" > "$tmp" && mv "$tmp" "$HISTORY"

slack_metrics "*comedy-tiktok-cross-post-daily:* $posted platform(s) / $post_ids" >/dev/null || true
echo "✅ cross-post: $posted platform(s) / $post_ids"
