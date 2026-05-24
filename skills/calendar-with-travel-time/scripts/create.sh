#!/usr/bin/env bash
# Create Google Calendar event with travel-time computed from home.
# Usage:
#   create.sh --title T --destination D --arrive-by ISO --duration MIN [--from F] [--calendar primary]
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB="$SKILL_DIR/data/known-distances.json"

TITLE=""; DEST=""; ARRIVE=""; DURATION=""; FROM="<your-address>"; CAL="primary"; BUFFER="default"
while [ $# -gt 0 ]; do
  case "$1" in
    --title) TITLE="$2"; shift 2;;
    --destination) DEST="$2"; shift 2;;
    --arrive-by) ARRIVE="$2"; shift 2;;
    --duration) DURATION="$2"; shift 2;;
    --from) FROM="$2"; shift 2;;
    --calendar) CAL="$2"; shift 2;;
    --buffer) BUFFER="$2"; shift 2;;
    *) echo "unknown arg: $1" >&2; exit 1;;
  esac
done

for v in TITLE DEST ARRIVE DURATION; do
  if [ -z "${!v}" ]; then echo "ERR: --${v,,} required" >&2; exit 2; fi
done

# Lookup travel time
TRAVEL_MIN=$(jq -r --arg d "$DEST" '.from_home[$d].min // empty' "$DB")
METHOD=$(jq -r --arg d "$DEST" '.from_home[$d].method // "unknown"' "$DB")

if [ -z "$TRAVEL_MIN" ]; then
  # Try venue lookup
  STATION=$(jq -r --arg d "$DEST" '.comedy_venues[$d].nearest_station // empty' "$DB")
  WALK=$(jq -r --arg d "$DEST" '.comedy_venues[$d].min_from_station // empty' "$DB")
  if [ -n "$STATION" ]; then
    STATION_MIN=$(jq -r --arg s "$STATION" '.from_home[$s].min // empty' "$DB")
    if [ -n "$STATION_MIN" ]; then
      TRAVEL_MIN=$((STATION_MIN + WALK))
      METHOD="$STATION 経由 (駅まで $STATION_MIN min + 徒歩 $WALK min)"
    fi
  fi
fi

if [ -z "$TRAVEL_MIN" ]; then
  echo "⚠️  Unknown destination: $DEST" >&2
  echo "    fallback: OSM Nominatim geocode (rough estimate)..." >&2
  # Nominatim free geocode
  HOME_COORDS=$(curl -sS --max-time 10 "https://nominatim.openstreetmap.org/search?q=<your-address>&format=json&limit=1" -A "calendar-with-travel-time/0.1" | jq -r '.[0] | "\(.lat),\(.lon)"')
  DEST_COORDS=$(curl -sS --max-time 10 "https://nominatim.openstreetmap.org/search?q=$(printf '%s' "$DEST" | jq -sRr @uri)&format=json&limit=1" -A "calendar-with-travel-time/0.1" | jq -r '.[0] | "\(.lat),\(.lon)"')
  if [ -n "$HOME_COORDS" ] && [ -n "$DEST_COORDS" ] && [ "$DEST_COORDS" != "null" ]; then
    # Haversine + 平均 30 km/h (徒歩+電車)
    TRAVEL_MIN=$(python3 -c "
import math
h_lat, h_lon = map(float, '$HOME_COORDS'.split(','))
d_lat, d_lon = map(float, '$DEST_COORDS'.split(','))
R = 6371.0  # km
dlat = math.radians(d_lat - h_lat)
dlon = math.radians(d_lon - h_lon)
a = math.sin(dlat/2)**2 + math.cos(math.radians(h_lat)) * math.cos(math.radians(d_lat)) * math.sin(dlon/2)**2
c = 2 * math.asin(math.sqrt(a))
km = R * c
# 0.5 km 以下 = 徒歩、それ以上 = 電車 30 km/h + buffer 5 min
if km < 0.5:
    print(int(km / 4.5 * 60) + 2)
else:
    print(int(km / 25 * 60) + 5)  # avg 25 km/h で電車+徒歩
")
    METHOD="OSM Nominatim rough estimate (要確認)"
  else
    echo "❌ Cannot determine travel time for: $DEST" >&2
    echo "   Add it to $DB or specify --travel-min" >&2
    exit 3
  fi
fi

# Compute event_start / event_end
BUFFER_MIN=$(jq -r --arg b "$BUFFER" '.buffer_minutes[$b] // .buffer_minutes.default' "$DB")
TOTAL_OFFSET=$((TRAVEL_MIN + BUFFER_MIN))

# arrive_by - travel - buffer = event_start
EVENT_START=$(date -j -f "%Y-%m-%dT%H:%M" -v "-${TOTAL_OFFSET}M" "$ARRIVE" "+%Y-%m-%dT%H:%M:%S")
# arrive_by + duration + 30 (return buffer) = event_end
EVENT_END=$(date -j -f "%Y-%m-%dT%H:%M" -v "+$((DURATION + 30))M" "$ARRIVE" "+%Y-%m-%dT%H:%M:%S")
MEETING_END=$(date -j -f "%Y-%m-%dT%H:%M" -v "+${DURATION}M" "$ARRIVE" "+%H:%M")
START_TIME=$(date -j -f "%Y-%m-%dT%H:%M:%S" "$EVENT_START" "+%H:%M")
ARRIVE_TIME=$(date -j -f "%Y-%m-%dT%H:%M" "$ARRIVE" "+%H:%M")

DESCRIPTION=$(cat <<EOF
⏰ 移動込みスケジュール (calendar-with-travel-time):
  ${START_TIME}  家出発 (${FROM})
  ${ARRIVE_TIME}  ${DEST} 到着
  ${ARRIVE_TIME}  ${TITLE} 開始
  ${MEETING_END}  終了予定

📍 移動: ${TRAVEL_MIN} min via ${METHOD}
🛡 buffer: ${BUFFER_MIN} min
EOF
)

# gog calendar events insert
gog calendar events insert \
  --calendar "$CAL" \
  --summary "$TITLE" \
  --location "$DEST" \
  --description "$DESCRIPTION" \
  --start-datetime "${EVENT_START}+09:00" \
  --end-datetime "${EVENT_END}+09:00" \
  --reminder-minutes 60,30 \
  --json 2>&1 | tee /tmp/gog-cal-out.json

EVENT_ID=$(jq -r '.id // .event.id // "?"' /tmp/gog-cal-out.json 2>/dev/null || echo "?")

echo ""
echo "✅ event created: $EVENT_ID"
echo "   start:  $EVENT_START JST (家出発)"
echo "   end:    $EVENT_END JST"
echo "   travel: $TRAVEL_MIN min ($METHOD)"
echo "   buffer: $BUFFER_MIN min"
echo "   calendar: $CAL"
