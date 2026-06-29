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

## Progress (2026-06-21)
- ✅ **Slice 1 (foundation)** — `lib/transport/{index,calendar-composio}.js`; `events.js` reads via
  `getCalendar()`. 5 tests; full suite green; real 72h fetch identical (21 events). Auto-deployed clean
  (build=conv74-slice1). Composio default → live unchanged.
- ✅ **Slice 2 (travel)** — `travel.js` listEvents7d + createTravelBlock via the adapter. THE proven
  2-language duplication point is now adapter-based on cloud. 59/59 tests; real read (58 items).
  Auto-deployed (build=conv74-slice2).
- ⏳ **Slice 3** — `ask.js` + `telegram-reply.js` + `notify.js`: calendar list/patch via adapter, and a
  MAIL adapter (`mail-composio.js` wrapping Unipile send + inbox). Same mechanical pattern, low risk.
- ⏳ **Slice 4** — `calendar-gog.js` + `mail-gog.js` (local BYOK) behind LIFE_TRANSPORT=gog.
- ⏳ **Slice 5** — thin `~/life-manager` wrapper that runs THIS Node app with LIFE_TRANSPORT=gog +
  cloudflared (single user); retire `travel_fill.py` + `resolve.py`; OSS repo vendors `lib/`. ← the slice
  that touches Dais's live LOCAL caller → do on his machine with a real local call E2E.

## The 3 layers + WHY "cloud is not OpenClaw" (Dais 2026-06-21)
Architecture = 3 layers. (1) CALL bridge — already byte-identical. (2) LIFE-LOGIC — duplicated today,
#74 shares it. (3) HARNESS (who schedules/hosts): LOCAL = an OpenClaw SKILL (openclaw cron fires it);
CLOUD = a bare Node service (server.js setInterval) on Railway — NOT OpenClaw. That layer-3 mismatch is
the structural "different components" feeling.
Two ways to make layer-3 the same: UP = put cloud on OpenClaw (#72; hard — needs the realtime bridge
upstreamed + multi-tenant OpenClaw). DOWN = drop OpenClaw FROM local: run the SAME Node app
(`node server.js`) locally with LIFE_TRANSPORT=gog + cloudflared, single-user. The app's own loop is the
scheduler (the same one cloud uses). OpenClaw, if kept at all, is demoted to "the thing that launches the
node process" — NOT part of the architecture. DOWN is the pragmatic same-architecture: after #74 slice5,
all 3 layers are identical; only the transport adapter + host + env differ. This is THE design — local
and cloud are the same Node app, one run with gog, one run on Railway with Composio.

## Safety invariant
Every slice keeps Composio as the DEFAULT transport (no env set → composio) so the live cloud caller is
unchanged until the gog adapter is proven. Verify each slice with the existing tests + a real tick log
line + /health auto-deploy.
