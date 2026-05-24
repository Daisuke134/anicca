#!/usr/bin/env bash
# Shared gcal day-lock for ALL apply skills (Dais HARD RULE: no two events same day).
# Cross-skill + cross-agent: checks the REAL calendar. Requires gog >= 0.17.0.
#   source ~/.openclaw/skills/_shared/gcal-day.sh
#   gcal_day_has_event "2026-05-24"  # exit 0 = day already has a night event → SKIP
#   gcal_busy_dates 14               # prints busy dates (next N days)
#   gcal_free_nights 14              # prints FREE night dates (next N days) — for fill logic

gcal_day_has_event() {
  local d="$1" nxt js
  nxt=$(date -j -v+1d -f "%Y-%m-%d" "$d" +%F 2>/dev/null || gdate -d "$d +1 day" +%F)
  js=$(gog calendar events list --from "$d" --to "$nxt" --json 2>/dev/null) || return 1
  printf '%s' "$js" | python3 -c "
import json,sys
d='$d'
raw=sys.stdin.read()
i=raw.find('{')
try: data=json.loads(raw[i:], strict=False)   # strict=False: gog descriptions have raw newlines
except Exception: sys.exit(1)
for e in data.get('events',[]):
    s=e.get('start',{}); st=s.get('dateTime', s.get('date',''))
    if not st.startswith(d): continue
    summ=e.get('summary','')
    if '💼' in summ or '🎓' in summ: continue   # skip day job + school class
    t=st[11:16] if 'T' in st else '00:00'
    if t>='17:30' or 'T' not in st: sys.exit(0)  # evening commitment exists
sys.exit(1)
" 2>/dev/null
}

gcal_busy_dates() {
  local days="${1:-14}" i d
  for i in $(seq 0 $((days-1))); do
    d=$(date -v+${i}d +%F 2>/dev/null || gdate -d "+${i} days" +%F)
    gcal_day_has_event "$d" && echo "$d"
  done
}

gcal_free_nights() {
  local days="${1:-14}" i d
  for i in $(seq 0 $((days-1))); do
    d=$(date -v+${i}d +%F 2>/dev/null || gdate -d "+${i} days" +%F)
    gcal_day_has_event "$d" || echo "$d"
  done
}
