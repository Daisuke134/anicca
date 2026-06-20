# Life Manager — CANONICAL state & architecture (SSOT, supersedes earlier life-manager specs)

Date: 2026-06-21. This is the single source of truth for "how Life Manager works right now."
Update THIS file whenever the architecture changes. Supersedes 2026-06-14-life-manager-phone-restore-and-evolve,
2026-06-09-anicca-life-manager-fix-and-roadmap, and the WS6* design docs (which remain as history).

## One-line truth (verified from code 2026-06-21)
Both LOCAL and CLOUD use **Telnyx + Gemini Live (Charon)** and SHARE the exact same bridge files
(`call-bridge.cjs` 10.9K + `call-logic.js` 17.2K, byte-identical in `~/life-manager/call/lib/` and
`apps/life-call/lib/`). **Twilio is DEAD** — deleted after Twilio error 21216 ("Account not allowed to
call +81…") fraud-blocked the destination; both pivoted to Telnyx. The old Twilio code at
`~/.openclaw/skills/anicca-life-manager/` + `~/research/pipecat/sutando/` is stale/retired — do NOT read
it as current.

## What it does (identical logic both sides)
planner → schedule a Charon call at **T-15 / T-10 / T-5** before EVERY event (escalating: calm→firm→harsh).
travel → compare consecutive event locations → insert `🚆 移動` block with real transit time.
ask → location unknown → ask (email/Telegram) → reply written back onto the event.
notify → not left by departure → with approval, tell the people you're meeting you're late.
call → real two-way phone call: **Telnyx Call Control ↔ Gemini Live native-audio (voice = Charon)**.

## Two deploy targets, ONE intended codebase
```
            ┌══════ SHARED CORE (byte-identical both sides) ══════┐
            │  call-bridge.cjs + call-logic.js                    │
            │  = Telnyx media-stream ⇄ Gemini Live (Charon)       │
            └───────────────────┬──────────────────┬─────────────┘
   ╔════════════════════════════╪════╗   ╔═════════╪══════════════════════════╗
   ║ ① LOCAL  ~/life-manager/ (OSS,  ║   ║ ② CLOUD  apps/life-call/ (Railway) ║
   ║    BYOK, repo Daisuke134/        ║   ║    + apps/landing (Netlify)        ║
   ║    life-manager)                ║   ║                                    ║
   ║  scheduler = openclaw cron       ║   ║  scheduler.js = 60s loop (multi-   ║
   ║  runner-telnyx.mjs → Telnyx     ║   ║   tenant), server.js + dial.js     ║
   ║  wss = cloudflared quick tunnel  ║   ║  wss = stable Railway wss (no      ║
   ║   (URL rotates; Mac must be up)  ║   ║   cloudflared)                     ║
   ║  ask/travel/notify = local skills║   ║  ask.js/travel.js/notify.js (JS)   ║
   ║  calendar/gmail = gog CLI         ║   ║  calendar=Composio / gmail=Unipile ║
   ║  data = local files               ║   ║  data = Supabase lm_users (paid)   ║
   ║  onboarding = none (it's you)     ║   ║  onboarding = /lm web + @Life-     ║
   ║                                   ║   ║   ManagerBotbot Telegram (name/    ║
   ║                                   ║   ║   phone in chat, OAuth/pay in web) ║
   ║  user = you (your keys)           ║   ║  users = many subscribers + Stripe ║
   ╚═══════════════════════════════════╝   ╚════════════════════════════════════╝
```
README claims the local↔cloud diff is "isolated to `adapters/transport.{js,py}` + env." In reality the
cloud (apps/life-call) has its OWN ask/travel/notify/scheduler JS (duplicated logic) — so today it is
TWO partly-overlapping codebases. The shared part is only the call bridge.

## DETAILED ASCII — function/endpoint level (verified from code 2026-06-21)

### ① LOCAL  ~/life-manager/  (repo Daisuke134/life-manager, OSS, BYOK)
```
 openclaw cron (~/.openclaw) ── every ~10min ──▶ planner.js  (the brain; does NOT call)
   │  • CAL.list({from:"today",to:+HORIZON_DAYS,max:250})  via adapters/transport.js
   │      └─ LIFE_TRANSPORT=gog → gogTransport(): `gog calendar events list -j --account <acct>`
   │  • for EVERY timed event × OFFSETS[15,10,5] whose fire-time is future:
   │      toneFor(off): 15→calm  10→firm  5→harsh
   │      leaveTimeMs(ev,all): if a 🚆移動/[Travel] block ENDS at event.start → use its start
   │      register one-shot:  openclaw cron add --at <iso> --delete-after-run --tools exec
   │        --message "node call/call.js --event=<json> --urgency=<tone>"
   ▼ (at the exact minute the one-shot fires)
 call/call.js  placeCall() ─ runnerFor(provider): default runner-telnyx.mjs ─┐
                                                                              ▼
   runner-telnyx.mjs:  call-bridge.cjs --provider telnyx                 (env: TELNYX_API_KEY,
     → cloudflared quick tunnel  (PUBLIC wss, URL ROTATES each run)       GEMINI_API_KEY)
     → POST api.telnyx.com/v2/calls  { stream_url: wss://<tunnel>,
          stream_bidirectional_mode:rtp, codec:PCMU, stream_track:both_tracks }
            │
            ▼  Telnyx dials +<YOUR_E164>  ─ media stream (PCMU 8k) ⇄
 ┌──────────── SHARED CORE  call-bridge.cjs + call-logic.js ────────────┐
 │  Telnyx media frames  ⇄  Gemini Live native-audio (model gemini-2.x  │
 │  live, voice = Charon).  call-logic.js = system prompt (names the    │
 │  event + urgency tone), VAD, affective-dialog, places_search tool.   │
 └──────────────────────────────────────────────────────────────────────┘
 SIDE SKILLS (same repo, local cron):
   travel/travel_fill.py  → Directions → write 🚆移動 block to gcal (gog)
   ask/ask-local.js       → unknown location → gog Gmail send Q → poll reply → write back
   notify/notify.js       → late (motion gate) → approval → gog Gmail to attendees
   locate/locate.js       → Telegram Live Location share → LIFE_DATA_DIR/location/<id>.json
   agent/resolve.py       → Gemini maps event→place or crafts question (no regex, worldwide)
```

### ② CLOUD  apps/life-call/  (Railway, multi-tenant, managed keys, the LIVE paid product)
```
 server.js  :8080   build=agentic-ask-worldwide-v2   ── on boot starts 4 loops ──┐
   ├ GET  /health , /                → {ok, service:"life-call", ws:"/ws"}        │
   ├ POST /test-call {uid,sig}       → dashboard "Call me now" (HMAC uid+sig)     │
   ├ WSS  /ws  (?ev=…&urgency=…&sig) → Telnyx media ⇄ Gemini (SHARED CORE)        │
   └ POST /telegram (secret header)  → parseUpdate → onboarding / TG reply        │
        ▼                  ▼                  ▼                       ▼
  scheduler.js        travel loop         ask loop              onboard loop
  startScheduler()    startTravelLoop()   startAskLoop()        startOnboardLoop()
  tick() 60s          travelTick() 30min  askTick() 20min       2min
   │                   │                   │                     │
   │ supaUsers(): GET Supabase lm_users    │                     └ telegram-onboard.js:
   │   ?phone=not.is.null & paid=is.true   │                        nudge each TG user to
   │   & calendar_provider=eq.composio_gcal│                        their next step
   │                   │                   │
   │ events.js: Composio GOOGLECALENDAR_   │ travel.js:           ask.js (AGENTIC):
   │   EVENTS_LIST (per-user OAuth)        │  travelDecision(ev,  agentResolveLocation()
   │                   │                    │  prev,home) → Direc-  = Gemini fn-calling
   │ for ev × WAKE_LEVELS[{15,gentle},     │  tions API minutes    places_search loop
   │   {10,firm},{5,harsh}]:               │  → Composio PATCH/    → unresolved? send via
   │   eventKey=`uid|startIso|min`         │  CREATE [Travel] block Telegram(if chat_id)
   │   claimWake() → lm_wake_log (dedup,   │  (home→home guarded)   else Unipile email
   │     fail = already fired, skip)        │  ⚠ STATIC duration    → reply read by Gemini
   │   buildStreamUrl(ev,urgency) (signed)  │     = #71 accuracy bug → agentMatchReply →
   │   dial.js placeCall({to,streamUrl})    │                        Composio PATCH event
   ▼                                                              notify.js: "I'm late" →
  dial.js → POST api.telnyx.com/v2/calls  stream_url=wss://<railway>/ws            classifyLate→pick
   → Telnyx dials user ⇄ /ws ⇄ ┌─ SHARED CORE call-bridge.cjs + call-logic.js ─┐  event+attendee→
                               │  (BYTE-IDENTICAL to local; supports Telnyx AND │  Unipile email
                               │   Twilio frame shapes) ⇄ Gemini Live Charon    │  from user's Gmail
                               └────────────────────────────────────────────────┘
```

### ③ WEB  apps/landing/  (Next.js → aniccaai.com /lm, Netlify functions)
```
 /lm  LmClient.tsx   Step: login → calendar → gmail → phone → pay → dashboard
   │  (localStorage anicca.lm.step survives the OAuth redirect; strips ?paid=/?code= from URL)
   ├ login     → lm-onboard?action=google-start → Google OAuth → exchange → uid
   ├ calendar  → calendar-connect (Composio gcal OAuth) → marks calendar_provider=composio_gcal
   │              ONLY when the connection is ACTIVE
   ├ gmail     → unipile-connect (Unipile, NO Google submission)
   ├ phone     → save +<dial><national> to lm_users
   ├ pay       → buy.stripe.com $20/mo (NEXT_PUBLIC_STRIPE_LM_URL; hidden if unset)
   │              → lm-stripe-webhook.js (dual secret: live + test) → set paid=true → ?paid=1
   └ dashboard → testCall() (gated on a saved phone) → POST life-call /test-call
 Telegram parity:  @LifeManagerBotbot  ── webhook ──▶ life-call POST /telegram
   • /start deep-link  → row by chat_id, native name/phone asked IN CHAT (telegram-onboard.js)
   • lm-onboard?action=telegram-link  saves telegram_chat_id (+ ?name= deep-link carry)
```

### UX FLOW — what the USER actually experiences (cloud has TWO entries: Web OR Telegram)
The cloud product onboards via EITHER the web form (/lm) OR the Telegram bot (@LifeManagerBotbot).
Both write the SAME `lm_users` row, SAME order (name→calendar→gmail→phone→pay→done). Only `name` +
`phone` differ: web = form fields, Telegram = typed natively in chat (NATIVE_STAGES). calendar/gmail/pay
always need the web (OAuth/Stripe) — on Telegram the bot sends a button to `/lm?tg=<chat_id>` that
resumes at the right step.
```
 ENTRY ① WEB /lm                         ENTRY ② TELEGRAM @LifeManagerBotbot
  ● login   Sign in with Google           /start → bot:"name?"  ← typed in chat (NATIVE)
  ● calendar Connect gcal (Composio) ◀──── bot button → /lm?tg=… (OAuth on web, shared)
  ● gmail    Connect Gmail (Unipile) ◀──── bot button (OAuth on web, shared)
  ● phone    +<cc><national>                bot:"phone?"  ← typed in chat (NATIVE)
  ● pay      Stripe $20/mo          ◀──── bot button → Stripe (shared)
  ● done ✅  Dashboard "Call me now"        bot:"🎉 all set"
        └──────────────┬──────────────────────────┬─────────┘
                       ▼ same cloud, same Supabase lm_users(paid=true)
 DAILY (both entries, user does nothing): calendar →⏰scheduler→📞15/10/5 calm/firm/harsh
   · 🚗travel→🚆移動 block · 📧ask unknown location via TG/Gmail · 📨notify late→attendee mail
```
LOCAL (~/life-manager) has NO onboarding UI — you clone, put your own TELNYX/GEMINI keys in .env, auth
your own gcal/gmail via gog, register planner in openclaw cron. Daily experience is IDENTICAL to cloud;
only the backstage differs (your keys + cloudflared tunnel vs managed keys + stable Railway wss). The
in-call Charon conversation is the SHARED CORE, byte-identical.

## DATA (Supabase) + KEYS
```
 lm_users : uid · name · phone · paid · calendar_provider(composio_gcal) · gmail_account_id(Unipile)
            · home_address · telegram_chat_id · tg_onboard_stage
 lm_wake_log : (uid,event_key) UNIQUE  ← claimWake() dedup so each (event,level) calls once
 lm_ask_log  : ask/reply audit
 Keys: LOCAL = your own (gog keychain, your GEMINI/TELNYX).  CLOUD = managed (Composio, Unipile,
       one TELNYX + one GEMINI we pay for, Stripe live+test, Supabase service role).
```

## Cloud runtime detail (apps/life-call on Railway, the live product)
server.js → /health, /test-call, /ws (Telnyx↔Gemini), /telegram (bot webhook). On boot starts 4 loops:
- ⏰ scheduler 60s — ALL upcoming real events × T-15/10/5, escalating urgency, dedup per (uid,event,level).
- 🚗 travel 30min — Directions API → [Travel] blocks (home→home guarded). **Uses STATIC duration — see #71.**
- 📧 ask 20min — Gemini function-calling `places_search` resolves locations; unresolved → email/Telegram; reply read by Gemini.
- 🤖 onboard 2min — nudges Telegram-linked users to their next onboarding step.
- 📨 notify — user says "I'm late" → Gemini finds the event+attendee → sends late email from their Gmail.
Data: Supabase `lm_users` (uid/name/phone/paid/calendar_provider/gmail_account_id/telegram_chat_id/
tg_onboard_stage/home_address), `lm_wake_log`, `lm_ask_log`. Per-user gcal = Composio OAuth, gmail = Unipile.
Deploy: `railway up . --path-as-root` (GitHub auto-deploy NOT wired). Landing = GitHub push → Netlify.
Pay: Stripe $20/mo (LIVE link + sandbox test link, webhook dual-secret live+test).

## VERIFIED WORKING (no-mock, this product, dated 2026-06-19/21)
- Cloud scheduler autonomously dialed a real seeded event at T-15/T-10/T-5 (real Telnyx ccid). ✅
- Agentic ask: 松竹/JETRO auto-fill, 歯医者 asks, reply fills the real calendar (3/3 E2E). ✅
- Travel home→home noise fixed (11 unit tests + E2E). ✅ Notify classify+pick verified. ✅
- Telegram onboarding deployed: name/phone native in chat, bot guides each step (name-save E2E). ✅
- Calendar reconnect via camofox (Composio OAuth) restored. ✅
- **#71 Routes API traffic-aware travel time DONE + DEPLOYED 2026-06-21** ✅ — cloud + local both query
  traffic-aware DRIVE (computeRoutes TRAFFIC_AWARE_OPTIMAL) + transit anchored to event start, return
  max(); ×1.4 fudge gone. VSDD adversary gate PASS (6/6, round 2). 26 unit tests. Live: life-call
  `/health` build=routes-api-traffic-aware-v1. (Railway CLI re-auth + `railway up`; auto-deploy still
  manual → #73.)
- **#69 wake/travel importance filter DONE + DEPLOYED 2026-06-21** ✅ — scheduler wakes ONLY for events
  you must travel to (travel-only default + per-user wake_policy; routines/at-home skipped) and anchors
  15/10/5 to DEPARTURE (the [Travel] block, or an origin-aware inline directionsMinutes when no block
  yet). 6h horizon, tolerance window, supaUsers fail-safe, wake_policy migration applied. Real-calendar
  E2E: 20 commitments → 4 wakes. VSDD gate PASS 6/6 (round 2 + residual closed). 54 tests. Live
  build=wake-importance-filter-v3. ★ Both launch blockers (#71 accuracy + #69 spam) now CLEAR. ★

## REMAINING TODO (canonical, launch-ordered)
1. **#71 WS6o — Routes API migration (ACCURACY / never-late, ~launch-blocker).** travel.js reads
   Directions STATIC `duration` (ignores traffic) for driving + ×1.4 fudge → underestimates in rush
   hour → user late. Our key ALREADY supports Routes API (computeRoutes TRAFFIC_AWARE worked). Migrate
   to `routes.googleapis.com/directions/v2:computeRoutes`, `routingPreference: TRAFFIC_AWARE_OPTIMAL`
   (= Google-Maps-grade), `trafficModel: PESSIMISTIC` (bias to leave early); transit → `arrivalTime`=event start.
2. **#69 WS6m — wake/travel importance filter (~launch-blocker).** Today = ALL events × 15/10/5 = 27
   calls/day for a busy calendar = users churn day 1. Default: only events you must TRAVEL to (real
   location ≠ home); routine/no-location = skip (per-user `wake_policy: travel-only|all-events`). Travel:
   skip if the user already has a buffer/their own travel block before the event.
3. **#70 WS6n — users without Google Calendar.** Add Outlook (Composio) + agentic "tell me your schedule" chat fallback.
4. **#61 WS6h / #67 #68 — full fresh-user E2E.** Web: incognito /lm (login→connect→phone→sandbox pay→dashboard);
   Telegram: /start (name→calendar→gmail→phone→pay→done). Dais confirms.
5. New — **GitHub→Railway auto-deploy** for life-call (today manual `railway up`; caused "old code deployed" pain).
6. **#45/#50 — demo-reel:** call transcript + screenshot → reelclaw → daily @anicca.comedy (TikTok/X).
7. **#51 — LAUNCH: Product Hunt + X.** Ship the product publicly. (Needs #71+#69 done first so new users aren't spammed/late.)
8. **#29 — STEP2:** Dais dogfoods on web; manage everyone's life.
9. **#72 WS6p (post-launch) — UNIFY onto OpenClaw.** OpenClaw's `@openclaw/voice-call` plugin supports
   Telnyx + Gemini Live realtime BUT realtime full-duplex is documented Twilio-Media-Streams-only —
   so our Telnyx+Gemini-Live bridge is the missing piece. Plan: upstream our bridge as a Telnyx-realtime
   provider → run OpenClaw-on-server (voice-call telnyx + multi-agent routing per-user + cron + Composio)
   → ONE codebase deploys local (BYOK) or server (subscribers). Retires the bespoke life-call + local sutando.
   DO AFTER LAUNCH — don't rebuild the working system first.

## #71 IMPLEMENTATION CONTRACT (Routes API migration — in progress)
Replace `directionsMinutes(src,dst,mapsKey)` in `apps/life-call/lib/travel.js` (and mirror to
`~/life-manager/travel/`) with a Routes-API call. Contract:
- **Input**: src address, dst address, mapsKey, departAtMs (when the user would leave), arriveByMs (event start).
- **DRIVE**: POST `https://routes.googleapis.com/directions/v2:computeRoutes`, header
  `X-Goog-FieldMask: routes.duration`, body `{origin:{address},destination:{address},travelMode:"DRIVE",
  routingPreference:"TRAFFIC_AWARE_OPTIMAL", departureTime:<future ISO>}`. Read `routes[0].duration`
  ("1234s"). **Remove the ×1.4 fudge** — traffic is now real.
- **TRANSIT**: VERIFIED 2026-06-21 that Routes API TRANSIT (`computeRoutes` travelMode:"TRANSIT")
  returns NO routes for our key/region (empty `{}` even between major stations). So TRANSIT stays on
  **legacy Directions** `maps/api/directions/json?mode=transit`, anchored to the event via
  `arrival_time=<event start unix seconds>` (NOT `departure_time=now` — the event is hours/days out, so
  "now" traffic/schedule would under-estimate). Read `routes[0].legs[0].duration.value`.
- **Order / never-late invariant**: query BOTH transit and traffic-aware drive, then return the LARGER
  of the two (we don't yet know the user's mode → assume the slower so we NEVER under-estimate). Floor
  5 min. Return null only if NEITHER resolves (caller then asks). [TODO #69/#70: per-user travel_mode
  pref → trust the chosen mode instead of max().]
- **Fallback**: non-200 / empty routes / missing duration / network throw → that mode returns null.
- **REGION REALITY (verified live 2026-06-21)**: Google provides NO transit directions for JAPAN via
  either Routes API OR legacy Directions (`新宿駅→東京駅` = ZERO_RESULTS both APIs; licensing). Legacy
  transit DOES resolve elsewhere (London Westminster→Tower Hill = OK). So in Japan every request falls
  to the traffic-aware DRIVE number — the only figure Google returns. HONEST CAVEAT: drive in-vehicle
  time can UNDER-estimate a rail door-to-door (no station walk + scheduled-train wait), so this is NOT
  strictly never-late for JP rail commuters; mitigated by `bufferMin` and the #69/#70 per-user
  travel_mode follow-up. Outside Japan max(transit, drive) works as intended. Legacy DRIVING works for
  the key — only JP transit data is absent.
- **Tests (RED first)**: parseDurationSeconds("1234s")→1234; minutesFromRoutes mock 1002s→17; DRIVE body
  has TRAFFIC_AWARE_OPTIMAL + departureTime≥now; TRANSIT body has arrivalTime and NO routingPreference.
- **E2E (no-mock)**: real LIFE_MAPS_KEY, 新宿区南元町→東京駅, assert minutes in plausible band + that a
  rush-hour departureTime yields ≥ the off-peak number.

## #69 IMPLEMENTATION CONTRACT (wake/travel importance filter — launch blocker, in progress)
Problem: scheduler.js tick() currently wakes for EVERY upcoming non-helper event × 15/10/5 = up to 27
calls/day for a busy calendar = day-1 churn. AND it anchors wakes to event.start, so a 30-min-travel
event gets called 15/10/5 min before the EVENT — i.e. AFTER the user should have left = useless/late.
Two pure changes in `apps/life-call/lib/` + scheduler.js (mirror intent to local planner where relevant):
- **(A) Importance filter** — `shouldWake(ev, home, policy)` pure fn:
  - `isHelperBlock(ev.summary)` → false (never wake for our own [Travel]/[PENDING]/[APPLIED]).
  - `policy === "all-events"` → true for any timed non-helper event (opt-in to the old behavior).
  - default `policy === "travel-only"` → true ONLY if ev has a real location AND normalized(location) ≠
    normalized(home); no-location or at-home events (routines: 🧘/😴/"call mom") → false. This is the
    "only events you must travel to" rule and kills routine spam.
  - Add `wake_policy` column to lm_users (text, default 'travel-only'); supaUsers selects it; null → 'travel-only'.
- **(B) Leave-time anchor (never-late)** — tick() anchors the 15/10/5 levels to DEPARTURE, not ev.start.
  `departureMs(ev, allEvents)` (pure): the latest `[Travel]` helper block ending within [start-2min,
  start+1min] of ev.start → its startMs (tolerance window because travel.js caps block duration at 59
  min, so a ~59.6-min leg ends ~1 min early); else ev.start. `resolveDeparture(ev, events, {home, mapsKey,
  directionsFn})` (async): if a block pins the leave time use it; ELSE (travel loop runs only every 30
  min, or the event was just added, or leaveMs was already past) compute the leave time INLINE via
  directionsMinutes so a must-travel event still wakes before departure instead of anchoring late to
  ev.start. directionsFn injected → unit-testable. eventKey stays per-(uid,event,level). Horizon = 6h so
  a long-travel event + its block are both visible when the T-15-before-departure wake is due.
- **FAIL-SAFE plumbing**: supaUsers selects `…,wake_policy`; if that 400s (column absent) it RETRIES the
  select WITHOUT wake_policy (→ undefined → travel-only) rather than returning [] — a missing column must
  never silently disable wakes fleet-wide. Migration committed at apps/life-call/migrations/2026-06-21-
  wake_policy.sql (applied live to Supabase cycgdwndgfgdbnndithc via Management API 2026-06-21).
- **Tests (RED first)**: shouldWake travel-only — home→skip, no-location→skip, real venue→wake, helper→skip,
  all-events→wake routine; departureMs — travel block present→its start, absent→event start, [Travel] not
  ending at start ignored. **E2E (no-mock)**: seed a busy day (3 routines + 1 venue event with a [Travel]
  block) → only the venue event triggers a wake, fired ~15 min before the travel-block start, verified
  against lm_wake_log + a real ccid (or dry count if outside a wake window).
- **Deploy**: `railway up` (life-call), bump build marker, verify `/health` build + a live tick log line.

## Next bigger version (post-launch)
omni-channel chat (reply to gmail/slack/discord/whatsapp/imessage with approval) · proactive buddy
(lead the user to their best self) · $10k MRR.
