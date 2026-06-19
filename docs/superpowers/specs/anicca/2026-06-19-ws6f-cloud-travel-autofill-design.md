# WS6f — Cloud travel-time auto-fill ([Travel] blocks, today + 7 days, every 30-60 min)

**Goal:** the cloud keeps each user's Google Calendar filled with `[Travel]` blocks for the next 7 days,
refreshed every 30-60 min, so the wake call fires before the user must LEAVE (not before the event
starts). Mirrors the local `travel/travel_fill.py`, ported to the Railway `life-call` service.

## The "leave from where" problem (the key design decision)

A travel block needs an origin. Three sources, used in priority order (agentic, not hardcoded):
1. **Previous event's location** — for back-to-back events, travel is from the prior event's place.
2. **Home address** — for the first event of a day (or after a gap), travel is from home.
3. **Ask** — if home is unknown AND it's a first-of-day event, the ask-loop emails/messages the user
   "where are you leaving from?" once; the answer is stored as `lm_users.home_address`.

So onboarding does NOT need a mandatory home-address step — we collect it lazily via the ask-loop the
first time it's actually needed, and cache it. (Add `home_address text` to lm_users.)

## Algorithm (per user, per tick)

```
events = Unipile/Composio gcal list (now → now+7d, timed, singleEvents)
for ev in events where ev has a location AND no [Travel] block already precedes it:
    origin = prevEvent.location (if prev ends < 90 min before ev) else home_address
    if !origin: enqueue an ask("leave-from") once, skip ev this tick
    mins = GoogleDirections(origin → ev.location).duration   (LIFE_MAPS_KEY)
    leaveAt = ev.start - mins - buffer(5)
    create gcal event "[Travel] → <ev.summary>" from leaveAt to ev.start   (idempotent: skip if a
        [Travel] block with the same target+leaveAt already exists)
```

Dedup: never create a second `[Travel]` for the same event — match on the `[Travel] → <summary>` title
+ the event start. (Same rule the local travel_fill used via the `[Travel]` prefix.)

## Wake-call interaction

The WS6c scheduler already skips `[Travel]`/helper blocks when picking the "soonest REAL event". WS6f
makes the wake fire relative to the **leave time**: the scheduler's due-window keys off the `[Travel]`
block's start (= leaveAt) for located events, falling back to event-start for unlocated ones.

## Scheduling

A second loop in `life-call` (or a Railway cron): every 30 min, run the algorithm for every lm_users
row with a connected calendar. Throttled + idempotent so re-runs are cheap.

## Env

`LIFE_MAPS_KEY` (Google Directions, already used locally), `COMPOSIO_API_KEY` (gcal read+write),
Supabase. Add `home_address` to lm_users.

## Done = 4-D convergence (no-mock E2E)

A real located event on a test calendar with no travel block → after a tick, a correct `[Travel]`
block appears (verified by reading it back via gcal), leave-time matches a real Directions duration,
and re-running does NOT duplicate it.
