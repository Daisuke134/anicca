#!/usr/bin/env bash
# wake_event_ensure.sh — A12 (Dais 2026-05-31).
#
# Ensure a daily 🛏 wake event exists in gcal for every day in the next
# WAKE_HORIZON_DAYS (default 7), at profile.alarm.wakeTime (default 07:00 JST).
# Idempotent: skips days that already have a wake event.
#
# Uses _shared/lib/gcal-policy.sh (HARD RULE #19) for insertion.
set -uo pipefail

SHARED_LIB="$LIFE_MANAGER_REPO/skills/_shared/lib"
PROFILE="$HOME/.local/state/life-manager/identity/profile.json"

[ -f "$HOME/.local/state/life-manager/.env" ] && set -a && . "$HOME/.local/state/life-manager/.env" && set +a
: "${GOG_ACCOUNT:?GOG_ACCOUNT not set — populate $HOME/.local/state/life-manager/.env first}"

WAKE_HORIZON_DAYS="${WAKE_HORIZON_DAYS:-7}"

# Read wakeTime from profile
WAKE_TIME=$(jq -r '.alarm.wakeTime // "07:00"' "$PROFILE")
WAKE_TIME_WD=$(jq -r '.alarm.wakeWeekdays // .alarm.wakeTime // "07:00"' "$PROFILE")
WAKE_TIME_WE=$(jq -r '.alarm.wakeWeekends // .alarm.wakeTime // "07:00"' "$PROFILE")

# Fetch existing wake events in horizon to dedup
TODAY=$(date +%F)
HORIZON=$(date -v+${WAKE_HORIZON_DAYS}d +%F)
EXISTING=$(/opt/homebrew/bin/gog calendar events list -j \
  --account "$GOG_ACCOUNT" --from "$TODAY" --to "$HORIZON" \
  --all-pages --max 500 2>/dev/null \
  | jq -r '(.events // .) | .[]? | select((.summary // "") | test("🛏|wake|起床"; "i")) | (.start.dateTime // .start.date)' \
  | sort -u)

inserted=0
skipped=0

for i in $(seq 0 $((WAKE_HORIZON_DAYS-1))); do
  d=$(date -v+${i}d +%F)
  dow=$(date -j -f "%Y-%m-%d" "$d" +%u)  # 1=Mon ... 7=Sun
  if [ "$dow" -ge 6 ]; then
    wt="$WAKE_TIME_WE"
  else
    wt="$WAKE_TIME_WD"
  fi
  start_iso="${d}T${wt}:00+09:00"
  end_iso=$(date -v+30M -j -f "%Y-%m-%dT%H:%M:%S%z" "${d}T${wt}:00+0900" +"%Y-%m-%dT%H:%M:%S%z" 2>/dev/null | sed 's/\([+-][0-9][0-9]\)\([0-9][0-9]\)$/\1:\2/' || echo "${d}T${wt}:30+09:00")

  # Dedup: skip if a wake event already exists on this day
  if echo "$EXISTING" | grep -q "^${d}"; then
    skipped=$((skipped+1))
    continue
  fi

  bash "$SHARED_LIB/gcal-policy.sh" create \
    --summary "🛏 Wake up" \
    --from "$start_iso" \
    --to "$end_iso" \
    --location "" \
    --description "Auto-inserted by anicca-life-manager wake_event_ensure (HARD RULE #19). Relentless call mode (intensity=relentless, buffer=0)." \
    --account "$GOG_ACCOUNT" \
    --calendar primary \
    >/dev/null 2>&1 \
    && inserted=$((inserted+1)) \
    || echo "[wake-ensure] failed to insert ${d} ${wt}" >&2
done

echo "WAKE_ENSURE_RESULT: {\"inserted\":$inserted,\"skipped\":$skipped,\"horizon_days\":$WAKE_HORIZON_DAYS}"
