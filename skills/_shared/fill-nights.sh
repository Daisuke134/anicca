#!/usr/bin/env bash
# EVERY-NIGHT-FILL orchestrator (Dais: no night without a show, no double booking).
# Runs all Tokyo apply skills (each gcal-day-locked), then reports remaining holes.
# Sources covered today: AI Tinkerers (meetup), U&C + ペチカ (jp comedy). TCB = weekly cron.
# Holes that remain = dates where NO source has a show that night (genuine gap, surfaced to memory).
set -uo pipefail
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
source ~/.openclaw/skills/_shared/gcal-day.sh
DAYS="${DAYS:-14}"

echo "▶ fill-nights  $(date +%FT%T)  window=${DAYS}d"
echo "── BEFORE: free nights (holes) ──"
gcal_free_nights "$DAYS" | sed 's/^/  ❌ /'

echo "── run apply skills (each day-locked, applies to all open slots) ──"
DAYS=$DAYS ALL=true bash ~/.openclaw/skills/anicca-meetup-talk-applier/scripts/apply.sh tokyo 2>&1 | tail -2
DAYS=$DAYS ALL=true bash ~/.openclaw/skills/anicca-comedy-factory/scripts/jp-live-apply-daily.sh 2>&1 | tail -2

echo "── AFTER: remaining holes ──"
REMAIN=$(gcal_free_nights "$DAYS")
if [ -z "$REMAIN" ]; then
  echo "  ✅ no holes — every night booked"
else
  echo "$REMAIN" | sed 's/^/  ❌ still empty: /'
  # surface genuine gaps to memory so heartbeat keeps hunting more sources
  for d in $REMAIN; do
    curl -sS -X POST http://localhost:3111/agentmemory/observe -H 'Content-Type: application/json' \
      -d "{\"hookType\":\"manual\",\"sessionId\":\"fill-nights\",\"project\":\"anicca\",\"cwd\":\"$HOME/.openclaw\",\"timestamp\":\"$(date -Iseconds)\",\"content\":\"NIGHT HOLE $d — no AI LT / comedy show found in current discover sources. Need to widen discover (connpass firecrawl, lu.ma, たか7 なかの芸能小劇場, more amateur venues) to fill this night.\",\"tags\":[\"hole\",\"fill\",\"$d\"]}" >/dev/null 2>&1 || true
  done
fi
echo "✓ fill-nights done"
