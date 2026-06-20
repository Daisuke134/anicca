# #74 Convergence plan — one JS life-logic, transport adapter (staged, never break the live caller)

Goal: a v2 change is written ONCE. Today the Composio/Unipile coupling is spread across events.js,
travel.js, ask.js, notify.js, telegram-reply.js. Abstract it behind a transport adapter so the SAME
JS life-logic runs cloud (Composio/Unipile) or local (gog). Stage it; the live paid caller must keep
working at every step.

## The seam (measured 2026-06-21)
CALENDAR: GOOGLECALENDAR_EVENTS_LIST (events/ask/travel/notify/telegram-reply), _CREATE_EVENT (travel),
_PATCH_EVENT (ask, telegram-reply). MAIL: Unipile send + inbox (ask, notify).

→ Adapter interface:
  calendar.listEvents(uid, {timeMin, timeMax}) -> [{id,summary,location,start,end}]
  calendar.createEvent(uid, {summary,startMs,durationMin,location,description})
  calendar.patchEvent(uid, eventId, {location?,...})
  mail.send(to, subject, body) ; mail.listInbox({limit})

## Slices (each: tests + cloud unaffected + auto-deploy verify)
1. **Foundation (this slice).** `lib/transport/calendar-composio.js` (wraps current Composio calls,
   behaviour-identical) + `lib/transport/index.js` (`getCalendar(opts)` → composio now; LIFE_TRANSPORT=gog
   later). Migrate the smallest consumer `events.js` to call the adapter. Cloud output byte-identical
   (same event shape). Adversary gate + live tick verify.
2. travel.js → adapter (listEvents + createEvent). 3. ask.js + telegram-reply.js → adapter (list+patch+mail).
   4. notify.js → adapter (list + mail). 5. `calendar-gog.js` + `mail-gog.js` (local) + a thin
   `~/life-manager` wrapper that runs the same Node app with LIFE_TRANSPORT=gog. 6. retire travel_fill.py
   + resolve.py; OSS repo vendors lib/.

## Safety invariant
Every slice keeps Composio as the DEFAULT transport (no env set → composio) so the live cloud caller is
unchanged until the gog adapter is proven. Verify each slice with the existing tests + a real tick log
line + /health auto-deploy.
