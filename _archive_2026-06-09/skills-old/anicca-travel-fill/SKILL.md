---
name: anicca-travel-fill
description: |
  Scans gcal next 7 days. For every pair of adjacent events at different
  locations, computes Google Directions transit time and INSERTS a "🚆 移動"
  travel block in the gap if one isn't already there. Idempotent (state/
  travel_filled.json keeps inserted event ids).

  Runs every 3 h via openclaw cron — or whenever Anicca decides the gcal
  needs filling. Routine events at home (sleep / wake / meditation / meal /
  running) get their location auto-resolved to profile.identity.homeAddress
  so the algorithm never asks the LLM to invent a station.

metadata:
  tags: gcal, travel, scheduling
  requires:
    bins: [python3, gog]
    env: [GOOGLE_API_KEY, GOG_ACCOUNT, GOG_KEYRING_PASSWORD]
---

# anicca-travel-fill

Goal: every event in the user's calendar has an explicit travel block before it
so lateness_check can call him at exactly `event.start - travel - buffer`
instead of guessing.

## Algorithm

```
events = list_next_7d()
for prev, curr in adjacent_pairs(events):
    p_addr = resolve(prev.location)         # routine_at_home → home
    c_addr = resolve(curr.location)
    if distance(p_addr, c_addr) < 500m: continue
    if travel_block_already_in_gap(prev, curr): continue
    travel_min = google_directions(p_addr → c_addr)
    insert_event(
        summary="🚆 移動 prev_short → curr_short",
        start = curr.start - travel_min,
        end   = curr.start,
        location = c_addr,
        description = "Auto-inserted by anicca-travel-fill",
    )
    record_in(state/travel_filled.json)
```

## State

`state/travel_filled.json` = `{ "<prev_id>|<curr_id>": "<inserted_id>" }`.
Lets us re-run safely without duplication.

## Run

```bash
bash ~/.openclaw/skills/anicca-travel-fill/scripts/run.sh
```

## Cron

openclaw cron, every 3 h, all hours:

```
schedule: 0 */3 * * *
message : exec で次を実行: bash ~/.openclaw/skills/anicca-travel-fill/scripts/run.sh
```
