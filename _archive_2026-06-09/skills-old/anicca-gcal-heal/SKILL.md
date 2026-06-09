---
name: anicca-gcal-heal
description: |
  Scans gcal next 14 days every 15 min, finds events whose `location` field is
  empty but whose summary/description has a JP address baked in (e.g. day-job
  with " 〒NNN-NNNN..." in the title). PATCHES the event to fill the
  location field so all downstream skills (lateness_check, travel_fill, the
  call prompt) read a clean gcal record instead of running regex fallback
  every time.

  Also routine_at_home events (sleep / wake / meditation / meals / running)
  with empty location get patched to profile.identity.homeAddress.

  HARD RULE #19: every gcal event MUST have a location after this cron runs.
metadata:
  tags: gcal, heal, scheduling
  requires:
    bins: [python3, gog]
    env: [GOG_ACCOUNT, GOG_KEYRING_PASSWORD]
---

# anicca-gcal-heal

Goal: turn `location = ""` into `location = "<address>"` for every event we
can resolve, so the call prompt + travel-fill skip their regex hacks.

## Algorithm

```
events = list_next_14d()
for ev in events:
    if ev.location.strip(): continue
    addr, kind = resolve_event_destination(ev)
    if kind in ('home_routine', 'summary_extracted'):
        gog calendar update <ev.id> --location addr
        record_in(state/healed.json)
```

## State

`state/healed.json` = list of event ids we've already patched, with the
resolved address. Re-run is safe because after patching, ev.location is no
longer empty and the heal step skips.

## Cron

15 min, all hours:
```
schedule: */15 * * * *
message : exec で次を実行: bash ~/.openclaw/skills/anicca-gcal-heal/scripts/run.sh
```
