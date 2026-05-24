#!/usr/bin/env bash
# dais-x-feed-digest — daily X (Twitter) tech-feed digest for Dais
# - 5 queries via xAI Grok Responses API (x_search tool)
# - Save JSON to ~/.openclaw/workspace/dais-x-feed-digest/digest_YYYY-MM-DD.json
# - Post Slack #metrics with prefix `📰 [Dais News]`
#
# Idempotent: re-running on same date overwrites JSON + posts a new Slack message.
# Tool rule: Grok Responses API + x_search only. No Apify, no fallback.

set -euo pipefail

SKILL_DIR="$HOME/.openclaw/skills/dais-x-feed-digest"
WORK_DIR="$HOME/.openclaw/workspace/dais-x-feed-digest"
WATCHLIST="$SKILL_DIR/watchlist.json"
DATE_JST="$(TZ=Asia/Tokyo date +%Y-%m-%d)"
TIME_JST="$(TZ=Asia/Tokyo date +%H:%M)"
OUTPUT="$WORK_DIR/digest_${DATE_JST}.json"

mkdir -p "$WORK_DIR"

# Load env
if [ -f "$HOME/.openclaw/.env" ]; then
  set -a; . "$HOME/.openclaw/.env"; set +a
fi

: "${XAI_API_KEY:?XAI_API_KEY missing}"
: "${SLACK_BOT_TOKEN:?SLACK_BOT_TOKEN missing}"
SLACK_CHANNEL="${SLACK_CHANNEL_ID:-{{profile.channels.reportChannel}}}"

call_grok() {
  local prompt="$1"
  local body
  body=$(jq -n --arg p "$prompt" '{model:"grok-4-fast", input:$p, tools:[{type:"x_search"}]}')
  curl -sS --max-time 120 -X POST "https://api.x.ai/v1/responses" \
    -H "Authorization: Bearer $XAI_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$body"
}

extract_text() {
  jq -r '
    .output[]? | select(.type=="message") | .content[]? | select(.type=="output_text") | .text
  ' 2>/dev/null || echo ""
}

extract_citations() {
  jq -c '[.output[]? | select(.type=="message") | .content[]? | .annotations[]? | select(.type=="url_citation") | .url] // []' 2>/dev/null || echo "[]"
}

# Build digest JSON
echo '{"date":"'"$DATE_JST"'","executedAt":"'"$(TZ=Asia/Tokyo date -Iseconds)"'","status":"success","sections":[]}' > "$OUTPUT"

slack_blocks=""
section_count=0

while IFS=$'\t' read -r qid label prompt; do
  echo "[run.sh] Calling Grok for: $qid ($label)"
  resp=$(call_grok "$prompt")
  text=$(echo "$resp" | extract_text)
  cites=$(echo "$resp" | extract_citations)

  if [ -z "$text" ]; then
    err=$(echo "$resp" | jq -r '.error // "empty response"' 2>/dev/null || echo "parse-fail")
    text="(no result — $err)"
    cites="[]"
  fi

  jq --arg id "$qid" --arg label "$label" --arg text "$text" --argjson cites "$cites" \
    '.sections += [{"id":$id,"label":$label,"text":$text,"citations":$cites}]' \
    "$OUTPUT" > "$OUTPUT.tmp" && mv "$OUTPUT.tmp" "$OUTPUT"

  section_count=$((section_count + 1))
  sleep 2
done < <(jq -r '.queries[] | [.id,.label,.prompt] | @tsv' "$WATCHLIST")

# Build Slack message
SLACK_TEXT=$(jq -r --arg date "$DATE_JST" --arg time "$TIME_JST" '
  "📰 [Dais News] " + $date + " " + $time + " JST\n" +
  "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n" +
  ([.sections[] |
    "*" + .label + "*\n" + .text + "\n"
  ] | join("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"))
' "$OUTPUT")

# Slack chat.postMessage (truncate to 38000 chars to stay under 40000 limit)
SLACK_TEXT_TRUNC=$(printf '%s' "$SLACK_TEXT" | head -c 38000)

curl -sS -X POST "https://slack.com/api/chat.postMessage" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-type: application/json; charset=utf-8" \
  -d "$(jq -n --arg ch "$SLACK_CHANNEL" --arg t "$SLACK_TEXT_TRUNC" '{channel:$ch, text:$t, mrkdwn:true, unfurl_links:false, unfurl_media:false}')" \
  | jq -r '"slack-post: ok=\(.ok) ts=\(.ts // "")"'

echo "[run.sh] done. sections=$section_count output=$OUTPUT"
