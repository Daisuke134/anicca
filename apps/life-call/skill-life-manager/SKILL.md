# life-manager — OpenClaw Skill

Life Manager keeps you on time. It reads your Google Calendar, resolves where you need to be,
figures out when you must leave, and calls your phone before you have to go.

## What it does

For every upcoming event the agent autonomously decides:

- **Online / phone call** — no travel needed. It recognises this from the event summary and
  location (e.g. "Zoom", "電話", a URL). No action beyond the wake call at the right time.
- **Physical venue** — it looks up travel time from your current location (or wherever you just
  were) using Google Maps, then inserts a `[Travel]` calendar block so the wake call fires before
  you need to leave, not just before the event starts.
- **Unknown location** — if it cannot figure out where to go it asks you via your connected
  channel (Telegram if linked, otherwise Gmail). It reads your reply and fills in the location
  automatically, then proceeds with travel planning.

The judgment — online vs findable venue vs genuinely unknown — lives in `lib/ask.js` and is made
by the model, not by hardcoded rules. A few canonical examples guide it; edge cases are handled
by the agent.

## Cron entrypoints

Three one-shot scripts replace the `setInterval` loops that run inside Railway. The OpenClaw
gateway calls each script on its own schedule and manages the interval.

| Script | Function | Suggested cadence |
|---|---|---|
| `scripts/tick.js` | Wake-call pass — places T-15/10/5 Telnyx+Gemini calls for events due now | Every 60 s |
| `scripts/travel.js` | Travel-fill pass — inserts `[Travel]` blocks for the next 7 days | Every 30 min |
| `scripts/ask.js` | Ask/reply pass — asks users about missing locations, reads replies | Every 20 min |

Each script:
1. Loads env vars from the OpenClaw gateway (no `.env` file needed at runtime).
2. Calls the corresponding one-shot function from `../../scheduler.js`.
3. Exits 0 on success, exits 1 on error (logged to stderr so the gateway sees it).

## Required env vars

Supplied by the OpenClaw gateway. The scripts themselves read nothing directly — `scheduler.js`
pulls these from `process.env` internally.

| Var | Used by |
|---|---|
| `GEMINI_API_KEY` | All passes (voice bridge + agentic location resolve) |
| `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` | User registry + wake dedup log |
| `COMPOSIO_API_KEY` | Calendar read/write (Google Calendar via Composio) |
| `LIFE_MAPS_KEY` (or `GOOGLE_API_KEY`) | Travel time + Places lookup |
| `PUBLIC_WSS` | tick only — WebSocket URL for the Telnyx/Gemini bridge |
| `LM_CALL_SECRET` | tick only — HMAC secret that authenticates the bridge upgrade |
| `LM_TELEGRAM_BOT_TOKEN` | ask only — send/read Telegram messages |
| `UNIPILE_TOKEN` + `UNIPILE_DSN` | ask only — send/read Gmail via Unipile |

## Architecture notes

- **Pure core** (`lib/travel.js`, `lib/wake-filter.js`, `lib/events.js`) — deterministic
  geometry and calendar logic, fully tested, no side effects.
- **Effectful shell** (`lib/dial.js`, `lib/ask.js`, `scheduler.js`) — Telnyx calls, Gemini
  voice, Supabase writes. Tested via stubs.
- **This skill** (`skill-life-manager/scripts/`) — thin cron entrypoints only. No logic lives
  here; everything is delegated to `scheduler.js`.

The Railway Node app (`server.js` + `scheduler.js`) stays untouched and live. This skill wraps
it; both can coexist.
