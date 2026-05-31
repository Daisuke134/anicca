---
name: anicca-arrival-mail
description: |
  Detects when the user has arrived at the next event's destination
  (= Telegram Live Location within arrival_radius_for(dest)), and sends a
  short "I'm here" notification to the event organizer / attendees +
  Slack channel. Closes the lateness loop: anicca-life-manager calls + maybe
  anicca-renraku sends an apology if late, then this skill confirms when
  the user physically arrived.

  Trust record: stakeholders see the user is en-route + arrived + on-time
  or N min late, all without manual notification.
metadata:
  tags: arrival, trust-record, gmail, notification
  requires:
    bins: [python3, gog]
    env: [GOG_ACCOUNT, GOG_KEYRING_PASSWORD]
---

# anicca-arrival-mail

## Trigger

Runs every 5 min (= same cadence as lateness_check). For each upcoming
event in the next 4 hours that has an organizer or attendees:

  1. Reuse lateness_check.get_location() + resolve_event_destination()
  2. If haversine(current, dest) <= arrival_radius_for(dest) AND state
     hasn't already sent arrival for this event:
     - GET reverse_geocode for nice place name
     - send Gmail to organizer + attendees: "Anicca confirming: <name>
       arrived at <event> at <time>."
     - optionally announce to Slack #attendance
     - record event_id in state/notified.json so we don't re-send

## Cron

```
schedule: */5 * * * *
message : exec で次を実行: bash ~/.openclaw/skills/anicca-arrival-mail/scripts/run.sh
```

## Anti-spam

- One mail per (event_id, day) max
- Skip events with `intensity=quiet` in profile.alarm.eventStyles
- Skip routine_at_home events (= no organizer to notify)
- Honour quiet_hours (= same as lateness_check)
