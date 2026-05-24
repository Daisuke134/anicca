#!/usr/bin/env bash
# Daily X analytics: pull Postiz post + platform analytics, write daily snapshot.
#
# Cron: 23 JST daily.
# Output:
#   data/analytics-daily.json — append { date, platform, posts: [...] }
#   stdout: ✅ analytics: <N> posts, followers=<N>, impressions=<N>

set -euo pipefail

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
: "${POSTIZ_API_KEY:?POSTIZ_API_KEY missing}"

SKILL_DIR="$HOME/.openclaw/skills/anicca-x-marketing-skill"
DATA_DIR="$SKILL_DIR/data"
HISTORY="$DATA_DIR/posts-history.json"
ANALYTICS="$DATA_DIR/analytics-daily.json"
[ -f "$ANALYTICS" ] || echo '[]' > "$ANALYTICS"

INTEGRATION_ID=$(jq -r '.postiz_x_integration_id' "$DATA_DIR/config.json")
POSTIZ_API="https://api.postiz.com/public/v1"

# Last 7 days posts only (analytics are most relevant fresh)
if date -v-7d > /dev/null 2>&1; then
  CUTOFF=$(date -u -v-7d +%Y-%m-%dT%H:%M:%SZ)
else
  CUTOFF=$(date -u -d "-7 days" +%Y-%m-%dT%H:%M:%SZ)
fi

# Pull recent posts from history
RECENT_IDS=$(jq -r --arg c "$CUTOFF" '[.[] | select(.posted_at >= $c) | .post_id] | .[]' "$HISTORY")

# Per-post analytics
POST_ROWS="[]"
for pid in $RECENT_IDS; do
  resp=$(curl -sS "$POSTIZ_API/analytics/post/$pid" -H "Authorization: $POSTIZ_API_KEY" || echo '[]')
  # Skip if response isn't an array (404 / error object)
  if ! echo "$resp" | jq -e 'type == "array"' >/dev/null 2>&1; then
    continue
  fi
  # Compress to {post_id, metrics:{label:value}}
  row=$(echo "$resp" | jq --arg id "$pid" '
    {post_id: $id,
     metrics: ([.[] | {(.label): ((.data | last).total // (.data | last).value // 0)}] | add // {})}')
  POST_ROWS=$(echo "$POST_ROWS" | jq --argjson r "$row" '. + [$r]')
done

# Platform-level (correct endpoint: /analytics/{integration})
PLATFORM=$(curl -sS "$POSTIZ_API/analytics/$INTEGRATION_ID?date=7" \
  -H "Authorization: $POSTIZ_API_KEY" || echo '[]')
echo "$PLATFORM" | jq -e 'type == "array"' >/dev/null 2>&1 || PLATFORM='[]'

FOLLOWERS=$(echo "$PLATFORM" | jq '[.[] | select(.label | test("Follower"; "i")) | (.data | last) | (.total // .value // 0)] | first // 0')
IMPRESSIONS=$(echo "$PLATFORM" | jq '[.[] | select(.label | test("Impression"; "i")) | (.data | last) | (.total // .value // 0)] | first // 0')

# Write snapshot
SNAPSHOT=$(jq -n \
  --arg date "$(date +%Y-%m-%d)" \
  --argjson posts "$POST_ROWS" \
  --argjson platform "$PLATFORM" \
  --argjson followers "$FOLLOWERS" \
  --argjson impressions "$IMPRESSIONS" \
  '{date: $date, followers: $followers, impressions_7d: $impressions, posts: $posts, platform_raw: $platform}')

TMP=$(mktemp)
jq --argjson s "$SNAPSHOT" '. += [$s]' "$ANALYTICS" > "$TMP" && mv "$TMP" "$ANALYTICS"

POST_COUNT=$(echo "$POST_ROWS" | jq 'length')
echo "✅ analytics: ${POST_COUNT} posts, followers=${FOLLOWERS}, impressions_7d=${IMPRESSIONS}"
