#!/usr/bin/env bash
# comedy-live-discover-monthly — 月初 09 JST
#
# Flow:
#   1. trip-calendar.json から「これから 35 日以内」の lock された city/date を抽出
#   2. 各 city/date に対し、live-events/<city>-<YYYY-MM-DD>.json が無ければ
#      generate (firecrawl で venue scrape + hardcoded directory)
#   3. data/live-events/<city>-<date>.json に save
#   4. Slack #metrics に candidate list を alert
#
# stdout last line: ✅ live-discover: <N> trips processed (<file paths>)

set -euo pipefail

SKILL_DIR="$HOME/.openclaw/skills/anicca-comedy-factory"
DATA_DIR="$SKILL_DIR/data"
LIVE_DIR="$DATA_DIR/live-events"
mkdir -p "$LIVE_DIR"

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

source "$HOME/.openclaw/skills/sao-content-factory/lib/slack.sh"

NOW_S=$(date +%s)
H35=$(( 35 * 86400 ))

processed=0
files=""

# Iterate trips
TRIPS=$(jq -c '.trips[]' "$DATA_DIR/trip-calendar.json")
while IFS= read -r trip; do
  city=$(echo "$trip" | jq -r '.city')
  date=$(echo "$trip" | jq -r '.date')
  trip_s=$(date -j -f "%Y-%m-%d" "$date" +%s 2>/dev/null || date -d "$date" +%s)
  diff=$(( trip_s - NOW_S ))
  # Skip past or > 35 days out
  [ "$diff" -lt 0 ] && continue
  [ "$diff" -gt "$H35" ] && continue

  out="$LIVE_DIR/${city}-${date}.json"

  # Already discovered — skip (idempotent)
  if [ -f "$out" ]; then
    files="${files}${out}\n"
    processed=$((processed + 1))
    continue
  fi

  # Generate by city directory (hardcoded venue DB + future firecrawl enrichment)
  python3 "$SKILL_DIR/scripts/lib/generate_candidates.py" \
    --city "$city" --date "$date" --out "$out"

  files="${files}${out}\n"
  processed=$((processed + 1))
done <<< "$TRIPS"

# Slack alert with primary recommendation per trip
SUMMARY="*comedy-live-discover-monthly:* $processed trip(s) processed"
for f in $(echo -e "$files" | grep -v '^$'); do
  c=$(jq -r '.city' "$f")
  d=$(jq -r '.date' "$f")
  v=$(jq -r '.primary_recommendation.venue // "(none)"' "$f")
  SUMMARY="${SUMMARY}\n• ${c} ${d}: ${v}"
done

slack_metrics "$(printf "%b" "$SUMMARY")" >/dev/null || true

echo "✅ live-discover: $processed trip(s) processed"
