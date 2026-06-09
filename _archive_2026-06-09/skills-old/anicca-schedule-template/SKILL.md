---
name: anicca-schedule-template
description: |
  For days where the user's gcal is empty (or nearly so), INSERT a default
  daily routine derived from profile.alarm.wakeTime + the per-day
  template. Critical for new OSS users — without this their first week
  feels broken because lateness_check has nothing to call about.

  Idempotent: skips any slot that already has an event in gcal. Routine
  events get location=home automatically (HARD RULE #19, gcal-heal will
  pick them up too).

  Threshold: a "day" counts as empty if there are < `EMPTY_DAY_MIN_EVENTS`
  dateTime events in the 24h block. Default 2 (= sleep+wake counts as
  empty). Tuneable per user via env.

metadata:
  tags: gcal, schedule, default, onboarding
  requires:
    bins: [python3, gog]
    env: [GOG_ACCOUNT, GOG_KEYRING_PASSWORD]
---

# anicca-schedule-template

Default daily skeleton:

```
wakeTime         🛏  Wake up
wakeTime+0:30    🧘  Meditation
wakeTime+1:00    🏃  Running
wakeTime+1:30    🍳  Breakfast
wakeTime+2:30    💼  Deep work
12:00            🍱  Lunch
wakeTime+11:30   🚶  Walk
19:00            🍲  Dinner
21:00            📚  Wind down
sleepTime        😴  Sleep
```

Sleep time defaults to `wakeTime + 16h` if not configured.

## Cron

- daily 04:00 JST — fills empty days in the next 7-day horizon
- HORIZON_DAYS env override

## Limits

- Skips weekends (= leave user freedom). Override via FILL_WEEKENDS=1.
- Never overwrites existing events; only inserts missing slots.
- Logs which slots were inserted per day in state/template_inserted.json.
