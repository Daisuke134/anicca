#!/usr/bin/env bash
# Postiz API wrapper for X posting.
# Usage:
#   source ~/.openclaw/skills/anicca-x-marketing-skill/scripts/lib/postiz.sh
#   postiz_post_thread <integration_id> <tweets_json_array_file>
#
# tweets_json_array_file format:
#   [{"content": "tweet 1"}, {"content": "tweet 2"}, ...]
#
# Returns (stdout):
#   <postId>\t<state>\t<releaseURL>
# Returns non-zero on error.

set -euo pipefail

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

: "${POSTIZ_API_KEY:?POSTIZ_API_KEY missing in ~/.openclaw/.env}"

POSTIZ_API="https://api.postiz.com/public/v1"

postiz_post_thread() {
  local integration_id="$1"
  local tweets_file="$2"
  local now_iso
  now_iso=$(date -u +%Y-%m-%dT%H:%M:%S.000Z)

  # Build payload: each tweet object needs content + image:[]
  local value_json
  value_json=$(jq '[.[] | {content: .content, image: []}]' "$tweets_file")

  local payload
  payload=$(jq -n \
    --arg date "$now_iso" \
    --arg iid "$integration_id" \
    --argjson value "$value_json" \
    '{
      type: "now",
      date: $date,
      shortLink: false,
      tags: [],
      posts: [
        {
          integration: { id: $iid },
          settings: { who_can_reply_post: "everyone" },
          value: $value
        }
      ]
    }')

  local resp
  resp=$(curl -sS -X POST "$POSTIZ_API/posts" \
    -H "Authorization: $POSTIZ_API_KEY" \
    -H "Content-Type: application/json" \
    --data "$payload")

  local post_id
  post_id=$(echo "$resp" | jq -r '.[0].postId // empty')

  if [ -z "$post_id" ]; then
    echo "POSTIZ POST FAILED: $resp" >&2
    return 1
  fi

  # Poll up to 60s for PUBLISHED state
  local start end_ts state url
  start_ts=$(date -u +%Y-%m-%dT00:00:00Z)
  if date -v+2d > /dev/null 2>&1; then
    end_ts=$(date -u -v+2d +%Y-%m-%dT00:00:00Z)
  else
    end_ts=$(date -u -d "+2 days" +%Y-%m-%dT00:00:00Z)
  fi

  for i in $(seq 1 12); do
    sleep 5
    local list
    list=$(curl -sS "$POSTIZ_API/posts?display=week&startDate=$start_ts&endDate=$end_ts" \
      -H "Authorization: $POSTIZ_API_KEY")
    state=$(echo "$list" | jq -r --arg id "$post_id" '.posts[] | select(.id==$id) | .state // empty' | head -1)
    url=$(echo "$list" | jq -r --arg id "$post_id" '.posts[] | select(.id==$id) | .releaseURL // empty' | head -1)
    if [ "$state" = "PUBLISHED" ] && [ -n "$url" ]; then
      printf '%s\t%s\t%s\n' "$post_id" "$state" "$url"
      return 0
    fi
  done

  printf '%s\t%s\t%s\n' "$post_id" "${state:-UNKNOWN}" "${url:-}"
  return 0
}

postiz_get_post() {
  local post_id="$1"
  local start_ts end_ts
  start_ts=$(date -u +%Y-%m-%dT00:00:00Z)
  if date -v-7d > /dev/null 2>&1; then
    start_ts=$(date -u -v-7d +%Y-%m-%dT00:00:00Z)
  else
    start_ts=$(date -u -d "-7 days" +%Y-%m-%dT00:00:00Z)
  fi
  if date -v+2d > /dev/null 2>&1; then
    end_ts=$(date -u -v+2d +%Y-%m-%dT00:00:00Z)
  else
    end_ts=$(date -u -d "+2 days" +%Y-%m-%dT00:00:00Z)
  fi
  curl -sS "$POSTIZ_API/posts?display=week&startDate=$start_ts&endDate=$end_ts" \
    -H "Authorization: $POSTIZ_API_KEY" \
    | jq --arg id "$post_id" '.posts[] | select(.id==$id)'
}
