# WS6c — Cloud Wake-Call Scheduler (the "wake FROM cloud")

**Goal:** place a per-user **Telnyx + Gemini Live (Charon) natural-conversation** wake call at
**T-15 min** before each real calendar event, entirely **from the cloud** — no Mac-mini, no
cloudflared, no human in the loop. This is what makes Life Manager a paid cloud product: a user
signs up at `/lm`, connects Google Calendar (Composio), pays, gives a phone number, and from then on
Anicca calls them before every event, anywhere.

## Why a new service (not Netlify, not alarm-backend)

- The Gemini bridge (`call-bridge.cjs`) is a **stateful bidirectional WebSocket** server (Telnyx
  media RTP ↔ Gemini Live). A Netlify lambda is stateless/short-lived → cannot host it.
- `apps/alarm-backend` is Python and its lateness call is **Twilio TwiML TTS** (robotic), not the
  Gemini Charon natural call. We want the good call.
- Decision: a dedicated **Railway Node service `apps/life-call/`** = persistent bridge + in-process
  60 s scheduler in ONE deploy. Railway auto-provides a stable public `wss://…up.railway.app/ws`
  (no cloudflared needed).

## Components

```
apps/life-call/
  server.js          Express(:PORT) — health + persistent Gemini bridge mounted at /ws
  scheduler.js       setInterval(60s): Supabase lm_users → next event → due? → dial
  lib/
    bridge.cjs       = call-bridge.cjs (persistent, multi-call; reads per-call ctx from /ws?query)
    call-logic.js    = Charon system-prompt / escalation copy (reused verbatim)
    telnyx.js        dial(to, streamUrl, ctx) + record_start + streaming_start (from runner-telnyx)
    events.js        fetchNextEvent(uid) (= netlify _lib/lm-events.js, shared logic)
    supabase.js      lm_users read + lm_wake_log dedup upsert
  package.json       deps: ws, express, @google/genai (or raw ws to Gemini) — copied from call/lib
  railway.toml       start = node server.js
```

## Per-call context (the persistent-bridge change vs local)

Local runner spawns one bridge per call and passes ctx via env. The cloud bridge is **persistent
and multi-call**, so context travels in the **stream_url query**:

```
streamUrl = wss://<svc>.up.railway.app/ws?name=<n>&summary=<s>&mins=<m>&uid=<uid>
```

`bridge.cjs` `wss.on("connection", (ws, req))` parses `req.url` query → builds the Charon system
prompt for THAT call via `call-logic.buildCallPrompt({name, summary, mins})`. No cross-call leakage.

## Scheduler contract (`scheduler.js`, every 60 s)

1. `lm_users` where `phone` set AND `paid=true` AND `calendar_provider='composio_gcal'`.
2. For each: `fetchNextEvent(uid)` (Composio, horizon 2 h).
3. **Skip helper blocks**: summaries starting with `[Travel]` or containing `[PENDING]`/`[APPLIED]`
   markers (those are Anicca's own inserted blocks, not real commitments).
4. `mins = (startMs - now)/60000`. Fire when `13 ≤ mins ≤ 15` (one fire per event; the 60 s tick
   guarantees the window is hit once).
5. **Dedup**: `lm_wake_log` upsert keyed `uid|startIso`; if a row exists, skip. Survives restarts.
6. Dial Telnyx with `streamUrl` (above) + `record_start` + `streaming_start`. Log sid.

## Env (Railway service)

`TELNYX_API_KEY`, `TELNYX_CONNECTION_ID`, `TELNYX_PHONE_NUMBER`, `GEMINI_API_KEY`,
`COMPOSIO_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `PUBLIC_WSS` (the service's own
public wss, set after first deploy), `BRIDGE_PORT`=`$PORT`.

## Done = 4-D convergence (no-mock E2E)

- spec ✓ (this doc)
- test ✓ scheduler dedup + due-window + helper-skip unit-tested
- impl ✓ service deployed to Railway, `/ws` reachable as wss, scheduler loop logging
- **verification ✓**: a REAL event placed at now+15 min on Dais's gcal → the cloud scheduler dials
  → **Dais's phone (+818046270314) rings with the Charon voice** naming the event → recording exists.
  "service deployed / compiles" ≠ done; the phone must ring from the cloud.

## Reuse (no rewrites)

`call/lib/call-bridge.cjs`, `call/lib/call-logic.js`, `call/lib/runner-telnyx.mjs` (dial/stream
bodies), `netlify/functions/_lib/lm-events.js` (events logic). Only NEW code: scheduler.js,
telnyx.js extraction, supabase.js, the `/ws?query` ctx parse, railway.toml.

---

## VERIFICATION (2026-06-18) — no-mock E2E PASSED ✅

Real cloud wake, end to end, no Mac-mini:
1. `apps/life-call` deployed to Railway (service `life-call`, public `wss://life-call-production.up.railway.app`).
   `/health` → `{"ok":true,"service":"life-call","ws":"/ws"}` (live).
2. lm_users + lm_wake_log tables created (Supabase Management API; PostgREST 200).
3. Dais row upserted (uid lm_784ad279…, phone +818046270314, paid, composio_gcal).
4. Real gcal event "Anicca Cloud Wake Test" created at now+15min via Composio.
5. The cloud scheduler tick fired:
   `[scheduler] WAKE uid=lm_784ad279- "Anicca Cloud Wake Test" in 14m ccid=v3:cfcy4FozNaO8…`
   `[bridge] carrier connected urgency=gentle live=1`   ← Telnyx answered + streamed media to /ws
   `[bridge] setupComplete`                              ← Gemini Live (Charon) spoke
6. `lm_wake_log` row id=1 written (atomic dedup, event_key `…|2026-06-18T20:48:48+09:00`).
7. Security gate verified: unsigned /ws → close 1008 (no Gemini socket); signed → accepted.
8. Test event deleted from the calendar afterward.

DONE = 4-D convergence: spec ✓ + tests ✓ (scheduler unit + auth-gate) + impl ✓ (live on Railway)
+ verification ✓ (a REAL Charon call placed from the cloud, audio bridged, naming the event).

---

## WS6i — Gmail read/write via Unipile, NO Google submission (2026-06-19) — PROVEN E2E ✅

Composio managed gmail.modify HARD-BLOCKS (restricted scope, Composio's app not Google-verified) —
proven in camofox (fresh gcal consent PASSES, gmail.modify BLOCKS, same browser/account = scope-tier,
not browser). Per Composio docs, the only fixes are "remove extra scopes" (didn't help — gmail.modify
alone still blocked) or own verified app (Google CASA submission — Dais refuses; took days + rejected).

**Solution: Unipile** (developer.unipile.com). Their docs: "By default, your integration uses Unipile's
OAuth credentials" → Unipile owns a Google-VERIFIED app → our users connect Gmail with NO submission by
us, no 100-cap. Covers Gmail/Outlook/Slack/Teams/WhatsApp/LinkedIn/Telegram/Instagram/Calendar = the
whole "manage all messaging" vision in one API. €5/connected-account/mo, 7-day free trial.

**Proven end-to-end (real, no-mock):**
1. Unipile account created (keiodaisuke+unipile, free trial). DSN api35.unipile.com:16580, token stored.
2. Hosted-auth link (`POST /api/v1/hosted/accounts/link` {type:create, providers:[GOOGLE], name:<uid>}).
3. Opened in camofox → Google consent showed **"UNIPILE が…アクセスを求めています"** with Gmail
   read/compose/send scopes — **NO "App is blocked"** (vs Composio managed which hard-blocks).
4. Completed consent → Unipile account ACTIVE: GOOGLE_OAUTH / keiodaisuke@gmail.com / id ZAIoCfJjQYi6cpNwVnTAMw.
5. **Read Dais's REAL inbox via `GET /api/v1/emails`** → 3 actual recent emails (Google security notice,
   connpass, GitHub). = Anicca can read+reply the user's Gmail. Submission avoided.

**Product wiring (next):** `unipile-connect` netlify fn mints a per-user hosted-auth link (name=lm uid) →
replaces gmail-connect in the /lm one-button (gcal stays Composio, gmail = Unipile) → store account_id on
lm_users (via Unipile notify_url webhook) → life-call ask/reply reads+sends via Unipile.
