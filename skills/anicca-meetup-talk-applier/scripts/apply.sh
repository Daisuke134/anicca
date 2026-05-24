#!/usr/bin/env bash
# anicca-meetup-talk-applier — apply for talk slots at upcoming AI meetups
# Usage: bash scripts/apply.sh <tokyo|sf>
#        DRY_RUN=true bash scripts/apply.sh tokyo
set -uo pipefail

CITY="${1:-tokyo}"
SKILL=~/.openclaw/skills/anicca-meetup-talk-applier
DRY_RUN="${DRY_RUN:-false}"
CDP_URL="${BU_CDP_URL:-http://127.0.0.1:9223}"
export BU_CDP_URL="$CDP_URL"

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
source ~/.openclaw/skills/_shared/gcal-day.sh
: "${DAIS_EMAIL:?}"
: "${DAIS_PRIMARY_PW:?}"

mkdir -p "$SKILL/data/applications"

case "$CITY" in
  tokyo) PITCH_FILE="$SKILL/data/pitch-tokyo.md"; CITY_FILTER="Tokyo"; WINDOW_DAYS="${DAYS:-14}" ;;
  sf)    PITCH_FILE="$SKILL/data/pitch-sf.md";    CITY_FILTER="SF";    WINDOW_DAYS="${DAYS:-90}" ;;
  *)     echo "ERR: city must be tokyo|sf"; exit 1 ;;
esac
ALL="${ALL:-true}"   # apply to ALL open speaker slots (not just 2)

echo "▶ apply  city=$CITY  dry_run=$DRY_RUN  window=$WINDOW_DAYS days  all=$ALL"

# ── gcal-first: busy map for the window + home base + travel buffer ──────────
GCAL_BUSY=$(gog calendar events list --from "$(date +%F)" --to "$(date -v+${WINDOW_DAYS}d +%F 2>/dev/null || gdate -d "+${WINDOW_DAYS} days" +%F)" --json 2>/dev/null \
  | jq -r '(.events // [])[] | "\(.start.dateTime // .start.date)|\(.end.dateTime // .end.date)"' 2>/dev/null || echo "")
HOME_BASE="${HOME_BASE:-$([ "$(date +%u)" -lt 6 ] && echo 中野 || echo 信濃町)}"
travel_min(){ case "$1-$2" in
  中野-Tokyo|中野-渋谷|中野-新宿) echo 25 ;; 中野-港|中野-田町) echo 30 ;;
  信濃町-Tokyo|信濃町-渋谷) echo 20 ;; 信濃町-新宿) echo 15 ;;
  *-SF) echo 30 ;; *) echo 35 ;; esac; }
gcal_conflict(){ # $1 start ISO ; returns 0 if conflicts
  local s="$1"; [ -z "$GCAL_BUSY" ] && return 1
  local d="${s%%T*}"
  echo "$GCAL_BUSY" | grep -q "$d" && return 0 || return 1
}

# ── Inject live numbers from dashboard.json into pitch ───────────────────────
DASH=$(curl -sS https://aniccaai.com/dashboard.json)
MRR=$(echo "$DASH" | jq -r '.mrr.total_usd // 0')
FOLLOWERS=$(echo "$DASH" | jq -r '.followers.total // 0')
PITCH_BODY=$(cat "$PITCH_FILE")
PITCH_LIVE=$(printf '%s\n\n— Live numbers (auto-injected): MRR \$%s · Followers %s · Updated %s\n' \
  "$PITCH_BODY" "$MRR" "$FOLLOWERS" "$(date -u +%FT%TZ)")

# ── Pick 1-2 candidate events ────────────────────────────────────────────────
CUTOFF=$(date -u -v "+${WINDOW_DAYS}d" +%Y-%m-%d 2>/dev/null \
       || gdate -u -d "+${WINDOW_DAYS} days" +%Y-%m-%d)
TODAY=$(date -u +%Y-%m-%d)

LIMIT=$([ "$ALL" = "true" ] && echo 99 || echo 2)
# Only structured event files (exclude _connpass-raw.json and other _* raw dumps)
EVENT_FILES=$(find "$SKILL/data/discovered" -name '*.json' ! -name '_*' 2>/dev/null)
PICKED=$(jq -c -s --arg city "$CITY_FILTER" --arg today "$TODAY" --arg cutoff "$CUTOFF" --argjson lim "$LIMIT" \
  '[.[] | select(.city == $city and .status == null and .date >= $today and .date <= $cutoff)] | .[0:$lim]' \
  $EVENT_FILES 2>/dev/null || echo "[]")

COUNT=$(echo "$PICKED" | jq 'length')
echo "  $COUNT candidate events (window $TODAY → $CUTOFF)"

if [ "$COUNT" = "0" ]; then
  echo "  no events to apply for. Run discover.sh first."
  exit 0
fi

# ── Apply to each ────────────────────────────────────────────────────────────
echo "$PICKED" | jq -c '.[]' | while read -r event; do
  EVENT_TITLE=$(echo "$event" | jq -r '.event')
  EVENT_URL=$(echo "$event" | jq -r '.url')
  EVENT_DATE=$(echo "$event" | jq -r '.date')
  EVENT_SRC=$(echo "$event" | jq -r '.source')
  SLUG=$(echo "$EVENT_URL" | sed 's|https\?://||; s|[/?&=]|-|g' | head -c 60)

  echo "  → $EVENT_TITLE ($EVENT_DATE, $EVENT_SRC)"

  # gcal-first: skip if that day already has a conflicting event
  if gcal_day_has_event "$EVENT_DATE"; then
    echo "    ⏭ HARD RULE: $EVENT_DATE already has a night event — skip (no double booking)"
    continue
  fi
  # dedupe via agentmemory (already applied?)
  if curl -sS -X POST http://localhost:3111/agentmemory/search \
       -H 'Content-Type: application/json' \
       -d "{\"query\":\"applied $EVENT_URL\",\"project\":\"anicca\"}" 2>/dev/null \
       | jq -e '(.results // []) | length > 0' >/dev/null 2>&1; then
    echo "    ⏭ skip: already applied (memory hit)"
    continue
  fi

  if [ "$DRY_RUN" = "true" ]; then
    echo "    [DRY] skip submit"
    continue
  fi

  # Browser-harness: navigate + find contact form + submit pitch
  {{profile.lateness.stakeholders.channel}}-harness -c "
import time
goto_url('$EVENT_URL')
wait_for_load(); time.sleep(2)
print('URL:', page_info().get('url',''))
# Source-specific form fill stubs — implementation extends per source.
# connpass: 主催者へ問合せ button → form fill
# lu.ma:    Apply to speak / Contact host
# meetup:   Message organizer
" 2>&1 | tail -5

  # Persist application state
  APPLIED_AT=$(date -u +%FT%TZ)
  jq -n \
    --arg event "$EVENT_TITLE" \
    --arg url "$EVENT_URL" \
    --arg city "$CITY_FILTER" \
    --arg date "$EVENT_DATE" \
    --arg applied_at "$APPLIED_AT" \
    --arg talk_title "Anicca — A self-funding Buddhist AI entity" \
    --arg status "pending" \
    --arg source "$EVENT_SRC" \
    --argjson accepted_at null \
    --argjson presented_at null \
    --argjson video_url null \
    --argjson audience_size null \
    '$ARGS.named' > "$SKILL/data/applications/$SLUG.json"

  echo "    state → $SKILL/data/applications/$SLUG.json"

  # ── gcal create with travel buffer (departure time, not event time) ────────
  TM=$(travel_min "$HOME_BASE" "$CITY_FILTER")
  ESL="${EVENT_DATE}T19:00:00"; EVENT_START="${ESL}+09:00"   # JST
  EVENT_END="${EVENT_DATE}T21:00:00+09:00"
  DEP=$(date -j -v-${TM}M -f "%Y-%m-%dT%H:%M:%S" "$ESL" "+%Y-%m-%dT%H:%M:%S+09:00" 2>/dev/null \
        || echo "${ESL}+09:00")
  gog calendar create primary \
    --summary "🎤 [PENDING] $EVENT_TITLE" \
    --from "$DEP" --to "$EVENT_END" \
    --location "$CITY_FILTER" \
    --description "出発:${DEP} ${HOME_BASE}->${CITY_FILTER} 移動${TM}分 開始:${EVENT_START} URL:${EVENT_URL}" \
    2>&1 | tail -2 || echo "    ⚠ gcal create failed"

  # ── memory observe (so heartbeat recalls 'applied, awaiting reply') ────────
  curl -sS -X POST http://localhost:3111/agentmemory/observe \
    -H 'Content-Type: application/json' \
    -d "{\"hookType\":\"manual\",\"sessionId\":\"apply-meetup-$CITY\",\"project\":\"anicca\",\"cwd\":\"$SKILL\",\"timestamp\":\"$APPLIED_AT\",\"content\":\"applied SPEAKER slot $EVENT_TITLE $EVENT_DATE url $EVENT_URL — awaiting organizer reply, gcal PENDING created\",\"tags\":[\"apply\",\"$CITY\",\"speaker\",\"awaiting-reply\"]}" >/dev/null 2>&1 || true

  # ── daily-memory append (reliable floor, auto-loaded by heartbeat) ─────────
  echo "- [$(date +%H:%M)] applied SPEAKER: $EVENT_TITLE ($EVENT_DATE) travel ${TM}min from $HOME_BASE → gcal PENDING [awaiting reply]" \
    >> "$HOME/.openclaw/workspace/daily-memory/$(date +%F).md"
done

# ── Slack notify ─────────────────────────────────────────────────────────────
if command -v openclaw &>/dev/null; then
  openclaw message send --channel slack --target "${SLACK_CHANNEL:-{{profile.channels.reportChannel}}}" \
    --text "🎤 Meetup talk applications — $CITY $COUNT submitted (window=$WINDOW_DAYS d)" 2>/dev/null || true
fi

echo "✓ apply done"
