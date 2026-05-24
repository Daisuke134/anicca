#!/usr/bin/env bash
# anicca-comedy-factory — SF standup open-mic planner (weekly, 90d window)
# SF open mics are mostly LIST-BASED (sign name day-of), not ahead-apply forms.
# So this skill: discover SF mics in the 90d trip window → create gcal HOLDS →
# memory note (so heartbeat knows + reminds) → Dais signs the list on the night.
# Sources: The Setup (Tue), Cheaper Than Therapy, Punch Line Punch Up,
#          Cobb's, San Francisco open-mic listings.
# Usage: DAYS=90 bash scripts/sf-live-apply-weekly.sh
# Replayable by any agent.
set -uo pipefail

SKILL=~/.openclaw/skills/anicca-comedy-factory
DAYS="${DAYS:-90}"; DRY_RUN="${DRY_RUN:-false}"
FC=/opt/homebrew/bin/firecrawl
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
mkdir -p "$SKILL/data/sf-live"

NOW=$(date -u +%FT%TZ); TODAY=$(date +%F)
CUTOFF=$(date -v+${DAYS}d +%F 2>/dev/null || gdate -d "+${DAYS} days" +%F)
echo "▶ sf-comedy-plan  ${NOW}  window=${TODAY}-${CUTOFF}  dry=${DRY_RUN}"

# SF trip window: read from gcal (events tagged ✈ SF or location SF) in window.
# If a SF trip block exists, only hold mics within it. Else, surface candidates
# for Dais to pick the trip dates around (logged to memory + Slack).
SF_TRIP=$(gog calendar events list --from "$TODAY" --to "$CUTOFF" --json 2>/dev/null \
  | jq -r '(.events//[])[] | select((.summary//"")|test("SF|San Francisco|✈";"i")) | "\(.start.dateTime//.start.date)|\(.end.dateTime//.end.date)|\(.summary)"' 2>/dev/null || echo "")

if [ -n "$SF_TRIP" ]; then
  echo "  SF trip window(s) found in gcal:"
  echo "$SF_TRIP" | sed 's/^/    /'
else
  echo "  no SF trip block in gcal yet — surfacing recurring mics for trip planning"
fi

# Recurring SF open mics (stable weekly slots, list-based signup on the night)
cat > "$SKILL/data/sf-live/recurring-mics.json" <<'JSON'
[
  {"venue":"The Setup (Lost Weekend)","day":"Tue","time":"19:00","signup":"list day-of (arrive early)","area":"Mission"},
  {"venue":"Cheaper Than Therapy","day":"Thu","time":"20:00","signup":"booked + open spots","area":"Union Square"},
  {"venue":"Punch Line Punch Up open mic","day":"varies","time":"19:30","signup":"list/lottery","area":"Embarcadero"},
  {"venue":"Cobb's open mic","day":"varies","time":"19:00","signup":"list","area":"North Beach"}
]
JSON

# memory note so heartbeat keeps SF comedy on the radar during trip planning
curl -sS -X POST http://localhost:3111/agentmemory/observe -H 'Content-Type: application/json' \
  -d "{\"hookType\":\"manual\",\"sessionId\":\"plan-sf-comedy\",\"project\":\"anicca\",\"cwd\":\"$SKILL\",\"timestamp\":\"$NOW\",\"content\":\"SF standup open mics are list-based (sign day-of): The Setup Tue, Cheaper Than Therapy Thu, Punch Line Punch Up, Cobbs. When SF trip dates lock, create gcal holds for mics in that window. Coordinate with meetup-apply-sf-weekly (same trip).\",\"tags\":[\"comedy\",\"sf\",\"plan\",\"trip\"]}" >/dev/null 2>&1 || true

# If SF trip exists, create gcal holds for The Setup (Tue) + Cheaper Than Therapy (Thu) inside it
HELD=0
if [ -n "$SF_TRIP" ] && [ "$DRY_RUN" != "true" ]; then
  TRIP_START=$(echo "$SF_TRIP" | head -1 | cut -d'|' -f1 | cut -dT -f1)
  TRIP_END=$(echo "$SF_TRIP" | head -1 | cut -d'|' -f2 | cut -dT -f1)
  # iterate days in trip, hold Tue (The Setup) + Thu (Cheaper Than Therapy)
  d="$TRIP_START"
  while [ "$d" \< "$TRIP_END" ] || [ "$d" = "$TRIP_END" ]; do
    DOW=$(date -j -f "%Y-%m-%d" "$d" +%u 2>/dev/null || gdate -d "$d" +%u)
    case "$DOW" in
      2) V="The Setup (Lost Weekend, Mission)"; T="19:00";;
      4) V="Cheaper Than Therapy (Union Square)"; T="20:00";;
      *) V=""; ;;
    esac
    if [ -n "$V" ]; then
      # depart 45min before (SF transit + list signup arrive-early), end +2h from showtime
      DEP=$(date -j -v-45M -f "%Y-%m-%dT%H:%M" "${d}T${T}" "+%Y-%m-%dT%H:%M:00" 2>/dev/null || echo "${d}T${T}:00")
      ENDH=$(( ${T%%:*} + 2 )); END="${d}T$(printf '%02d' $ENDH):${T#*:}:00"
      gog calendar create primary --summary "🎤 [SF mic] $V" --from "${DEP}" --to "${END}" \
        --location "San Francisco" --description "出発:${DEP} (移動45分+リスト記名で早着) 開演:${T} List-based signup — arrive early. SF trip mic. 遅刻厳禁" 2>&1 | tail -1 || true
      echo "- [$(date +%H:%M)] SF mic hold ${d} ${V} (depart ${DEP})" >> "$HOME/.openclaw/workspace/daily-memory/$(date +%F).md"
      HELD=$((HELD+1))
    fi
    d=$(date -j -v+1d -f "%Y-%m-%d" "$d" +%F 2>/dev/null || gdate -d "$d +1 day" +%F)
  done
fi

echo "✅ sf-comedy-plan: trip-windows=$(echo "$SF_TRIP" | grep -c . ) mics-held=$HELD (90d, list-based signup on the night)"
