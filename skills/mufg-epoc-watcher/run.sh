#!/usr/bin/env bash
# mufg-epoc-watcher — daily MUIT/MUFG EPOC AI intel brief for Dais
# - 5 queries via xAI Grok Responses API (x_search tool)
# - 1 synthesis call (Grok 4 fast, no tools) → "EPOC contribution 案 3 件"
# - Save JSON to ~/.openclaw/workspace/mufg-epoc-watcher/brief_YYYY-MM-DD.json
# - Post Slack #metrics with prefix `🏦 [MUFG/EPOC Daily]`
#
# Idempotent: re-running on same date overwrites JSON + posts a new Slack message.
# Tool rule: Grok Responses API + x_search only. No Apify, no fallback.

set -euo pipefail

SKILL_DIR="$HOME/.openclaw/skills/mufg-epoc-watcher"
WORK_DIR="$HOME/.openclaw/workspace/mufg-epoc-watcher"
WATCHLIST="$SKILL_DIR/watchlist.json"
DATE_JST="$(TZ=Asia/Tokyo date +%Y-%m-%d)"
TIME_JST="$(TZ=Asia/Tokyo date +%H:%M)"
OUTPUT="$WORK_DIR/brief_${DATE_JST}.json"

mkdir -p "$WORK_DIR"

# Load env
if [ -f "$HOME/.openclaw/.env" ]; then
  set -a; . "$HOME/.openclaw/.env"; set +a
fi

: "${XAI_API_KEY:?XAI_API_KEY missing}"
: "${SLACK_BOT_TOKEN:?SLACK_BOT_TOKEN missing}"
SLACK_CHANNEL="${SLACK_CHANNEL_ID:-{{profile.channels.reportChannel}}}"

call_grok_with_search() {
  local prompt="$1"
  local body
  body=$(jq -n --arg p "$prompt" '{model:"grok-4-fast", input:$p, tools:[{type:"x_search"}]}')
  curl -sS --max-time 180 -X POST "https://api.x.ai/v1/responses" \
    -H "Authorization: Bearer $XAI_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$body"
}

call_grok_synthesis() {
  local prompt="$1"
  local body
  body=$(jq -n --arg p "$prompt" '{model:"grok-4-fast", input:$p}')
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

# Build initial JSON
echo '{"date":"'"$DATE_JST"'","executedAt":"'"$(TZ=Asia/Tokyo date -Iseconds)"'","status":"success","sections":[],"synthesis":""}' > "$OUTPUT"

section_count=0
all_text=""

while IFS=$'\t' read -r qid label prompt; do
  echo "[run.sh] Calling Grok x_search for: $qid ($label)"
  resp=$(call_grok_with_search "$prompt")
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

  all_text="${all_text}

═══ ${label} ═══
${text}"

  section_count=$((section_count + 1))
  sleep 2
done < <(jq -r '.queries[] | [.id,.label,.prompt] | @tsv' "$WATCHLIST")

# Synthesis call → EPOC contribution 案 3 件
SYNTH_INSTRUCTION=$(jq -r '.synthesis_prompt' "$WATCHLIST")
SYNTH_PROMPT="${SYNTH_INSTRUCTION}

=== Today's 5 search results (raw) ===
${all_text}

=== End of search results ==="

echo "[run.sh] Calling Grok synthesis (no tools) for EPOC contribution 案 3 件"
synth_resp=$(call_grok_synthesis "$SYNTH_PROMPT")
synth_text=$(echo "$synth_resp" | extract_text)

if [ -z "$synth_text" ]; then
  synth_text="(synthesis failed — check Grok API)"
fi

jq --arg s "$synth_text" '.synthesis = $s' "$OUTPUT" > "$OUTPUT.tmp" && mv "$OUTPUT.tmp" "$OUTPUT"

# Build Slack message
SLACK_TEXT=$(jq -r --arg date "$DATE_JST" --arg time "$TIME_JST" '
  "🏦 [MUFG/EPOC Daily] " + $date + " " + $time + " JST\n" +
  "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n" +
  "_OpenClaw は MUFG データに触れない。Dais が社内に持ち込む人間レイヤー専用 brief。_\n\n" +
  ([.sections[] |
    "*" + .label + "*\n" + .text + "\n"
  ] | join("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")) +
  "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n" +
  "*🎯 EPOC contribution 案 3 件 (今日中に出せる)*\n" +
  .synthesis
' "$OUTPUT")

# Slack chat.postMessage (truncate to 38000 chars to stay under 40000 limit)
SLACK_TEXT_TRUNC=$(printf '%s' "$SLACK_TEXT" | head -c 38000)

curl -sS -X POST "https://slack.com/api/chat.postMessage" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-type: application/json; charset=utf-8" \
  -d "$(jq -n --arg ch "$SLACK_CHANNEL" --arg t "$SLACK_TEXT_TRUNC" '{channel:$ch, text:$t, mrkdwn:true, unfurl_links:false, unfurl_media:false}')" \
  | jq -r '"slack-post: ok=\(.ok) ts=\(.ts // "")"'

echo "[run.sh] done. sections=$section_count synthesis=$([ -n "$synth_text" ] && echo "ok" || echo "empty") output=$OUTPUT"
