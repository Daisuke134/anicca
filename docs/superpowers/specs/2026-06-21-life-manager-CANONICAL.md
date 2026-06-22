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

## REMAINING TODO (canonical, launch-ordered — full tasklist, mirrors the task tool)
### ✅ DONE + LIVE (2026-06-21)
- ~~**#71** Routes API traffic-aware travel~~ ✅ gate 6/6, live (build=routes-api-traffic-aware-v1).
- ~~**#69** wake/travel importance filter + leave-anchor~~ ✅ gate 6/6, live. ★ both launch blockers clear ★
- ~~**#73** GitHub→Railway auto-deploy~~ ✅ verified: `git push` → live ~180s, no `railway up`.
- ~~**#74 slice1** events.js → getCalendar() adapter~~ ✅ deployed (Composio still default).
- ~~**#74 slice2** travel.js → getCalendar() adapter~~ ✅ deployed (the proven 2-language dup point).
- ~~**#74 slice3** ask/notify/telegram-reply → getCalendar()+getMail() (Unipile mail adapter)~~ ✅ DONE +
  LIVE (build=conv74-slice3). VSDD gate PASS 7/7 (no call-site shape mismatch), 73/73 tests. ★ CLOUD-side
  convergence COMPLETE — ALL raw Composio/Unipile coupling now lives only in lib/transport/; the life-logic
  modules (events/travel/ask/notify/telegram) are fully provider-agnostic, ready for the gog adapter. ★

### 🔄 #74 CONVERGENCE — remaining (makes local == cloud architecture; Composio STAYS, just consolidated)
- **#75 slice3** — ask.js + notify.js + telegram-reply.js → getCalendar() + new mail adapter (Unipile).
  Consolidate the 5-file raw Composio coupling into calendar-composio.js + mail-composio.js. Composio
  remains the cloud provider + default → live caller unchanged. Finishes the CLOUD side of the adapter.
- ~~**#76 slice4** calendar-gog.js + mail-gog.js (LOCAL BYOK adapter)~~ ✅ DONE — gog 0.17.0 CLI
  (events list/create/update + gmail send/search/get), same interface, selected by LIFE_TRANSPORT=gog.
  Composio-dialect args translated to gog flags; argv flag-smuggling hardened (positionals reject /^-/,
  option values glued `--flag=value`); getCalendar/getMail fail-loud on unknown env. 71/71 tests + real
  gog E2E (15 events, gcal shape matches). Cloud stays composio (default) → live unchanged.
  ★ The whole transport adapter layer (composio + unipile + gog) now EXISTS — local can run the same JS. ★
- **#77 slice5** — local runs the SAME `node server.js` (LIFE_TRANSPORT=gog + cloudflared, launchd),
  app's own scheduler loop replaces openclaw cron --at; OpenClaw removed from the LM architecture
  (at most a launcher); retire travel_fill.py + resolve.py. ALL 3 layers then identical local↔cloud.
  REQUIRES a real local phone-call E2E on Dais's Mac before flipping.

### 🚀 LAUNCH readiness
- **#61 IN PROGRESS — two launch blockers found + fixed 2026-06-21:** (1) `/lm` Subscribe button was
  HIDDEN — `NEXT_PUBLIC_STRIPE_LM_URL` was unset; the build runs in GitHub Actions (`secrets.*`), so the
  fix was a GH Actions secret (sandbox link, Dais's choice) + rebuild → pay button now renders. (2) the
  deployed lm-stripe-webhook had `STRIPE_LM_WEBHOOK_SECRET` (live) but NOT `STRIPE_LM_WEBHOOK_SECRET_TEST`
  → sandbox/test-mode checkouts would 400 on signature → paid never flips. Fixed: set the test secret in
  Netlify site env (anicca2) + redeploy.
  ✅ **VERIFIED LIVE 2026-06-21**: signed checkout.session.completed → lm-stripe-webhook HTTP 200 →
  lm_users.paid flipped true (real deployed function + real Supabase write); test row cleaned. The
  payment→activation pipe works for a real /lm user. #61 remaining breakdown:
    - **#61-a** flip GH secret NEXT_PUBLIC_STRIPE_LM_URL to the LIVE link (…2880v) + rebuild → real $20/mo
      (needs Dais "go live"; live webhook secret already in Netlify).
    - **#61-b** full NEW-user onboarding incl. Composio gcal connect — human-gated (a fresh Google account;
      account creation is prohibited for the agent) → Dais dogfoods on a 2nd Google OR the first real user.
    - **#67/#68** Telegram full E2E (ask/notify deliver + read replies; interactive /start onboarding) —
      agent can do this solo on the live @LifeManagerBotbot. ← DOING NEXT.
    - **#63** Telegram onboarding parity with web — close after #67/#68.
  ✅ **#67/#68 VERIFIED LIVE (solo) 2026-06-21**: @LifeManagerBotbot (id 8834419975) webhook → life-call
  /telegram is wired (secret ok, 0 pending, no errors). Posted signed /start + name updates to the live
  webhook → HTTP 200, state machine correct: null row → "name" prompt; typing a name (for an unlinked
  chat) carries it via `/lm?tg=<chat>&name=<name>` and the ROW IS CREATED ON THE WEB calendar-connect
  step (by design — OAuth/Stripe need web), NOT by the Telegram handler. So no row from a chat that never
  reaches web = correct, not a bug. Telegram onboarding LOGIC is launch-ready; the only unverified piece
  is the same human-gate as #61-b: a real Telegram user doing /start + a fresh Google for the gcal connect.
  ★ BOTH web and Telegram onboarding converge on ONE human-gate: a fresh Google account's Composio gcal
  connect (agent can't create Google accounts) → Dais dogfoods on a 2nd Google, or the first real user. ★
- **#61** (incl #67/#68) — full fresh-paid-user cloud E2E: web incognito /lm (login→connect→phone→sandbox
  pay→dashboard) + Telegram /start (name→calendar→gmail→phone→pay→done), no manual seeding. Dais confirms.
- **#70** — users without Google Calendar: Outlook (Composio) + agentic "tell me your schedule" chat fallback.
- **#45/#50** — demo-reel pipeline: ① real-call material (transcript + ring + dashboard shot) → ② reelclaw
  9:16 render → ③ daily fresh (no rotation) → ④ auto-post TikTok/IG/X (@anicca.comedy) + releaseURL verify
  → ⑤ account-history ledger.
- **#51 — LAUNCH: Product Hunt + X.** Public/irreversible → Dais confirms before broadcasting. (After #61.)
- **#29 — STEP2:** Dais dogfoods on web; manage everyone's life.

### 🔭 Post-launch (optional, the grand ideal)
- **#72 — UNIFY onto OpenClaw.** Upstream call-bridge.cjs into @openclaw/voice-call as a realtime provider
  (the missing piece — voice-call is turn-based TTS today), then run ONE OpenClaw app local (gog) OR
  server (Composio, multi-tenant). #74 is the prerequisite step-1 of this staircase. Don't rebuild the
  working system first.

### Adjacent (non-LM, later)
- **#12** marketing article/video/hackathon · **#22** E2E harness (UX-SPEC + browser-use loop) · **#25**
  OSS anicca automaton loop + README · **#27** aniccaai.com IA redesign · **#28** UBI rails.

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

## WHY local=OpenClaw / cloud=Railway, and how to converge (the maintenance-cost answer)
Measured 2026-06-21: only `call-bridge.cjs` + `call-logic.js` are byte-IDENTICAL across local & cloud.
Everything else is implemented TWICE — and travel is even in two LANGUAGES (local `travel_fill.py` Python,
cloud `travel.js` JS). Proof of the tax: #71 had to be fixed in BOTH this session.

| concern | LOCAL ~/life-manager | CLOUD apps/life-call | shared? |
|---|---|---|---|
| call bridge (Telnyx⇄Gemini Charon) | call/lib/call-bridge.cjs + call-logic.js | lib/ same files | ✅ byte-identical |
| travel time | travel/travel_fill.py (Python) | lib/travel.js (JS) | ❌ dup, 2 languages |
| ask / resolve | ask/ask-local.js + agent/resolve.py | lib/ask.js | ❌ dup |
| notify | notify/notify.js | lib/notify.js | ❌ dup |
| planner / scheduler | planner.js → openclaw cron `--at` | scheduler.js → setInterval 60s | ❌ dup |
| calendar / gmail | gog CLI (your keychain) | Composio / Unipile (managed OAuth) | genuinely different (adapter) |
| public wss | cloudflared quick tunnel (rotates) | stable Railway URL | genuinely different (env) |
| data / registry | local files, single user | Supabase multi-tenant | genuinely different (adapter) |

WHY it ended up split: LOCAL was built first as an OpenClaw skill — OpenClaw already gives a local cron
(`openclaw cron --at`) + `gog` for Google + runs on your Mac with YOUR keys ("OpenClaw is just the
executor"). CLOUD cannot be OpenClaw-on-Mac: it must be always-on (your Mac sleeps), multi-tenant (each
paying user needs their own managed OAuth = Composio, not gog), have a STABLE public wss for Telnyx media
(cloudflared dies; Railway gives a permanent URL), plus Supabase + Stripe. And we couldn't "just run
OpenClaw on the server" because `@openclaw/voice-call` doesn't support our Telnyx+Gemini-realtime bridge
(documented Twilio-Media-Streams-only). So cloud got reimplemented in JS around the shared bridge → the
duplication you're worried about is REAL.

### Convergence plan (kill the double-maintenance) — split #72 into two levels
- **#74 — PRACTICAL convergence (do BEFORE/AROUND launch; no OpenClaw needed).** ONE JS codebase for the
  life-logic (planner/scheduler, travel, ask, notify) under `apps/life-call/lib/`. Abstract the genuine
  differences behind a `transport` adapter (calendar/gmail = gog | Composio; data = file | Supabase; wss =
  cloudflared | Railway; schedule = local loop | server loop) selected by `LIFE_TRANSPORT` env. LOCAL then
  = run the SAME Node app with `LIFE_TRANSPORT=gog` + cloudflared, single-user; CLOUD = `LIFE_TRANSPORT=
  composio` + Supabase + Stripe. RETIRE the duplicated Python (`travel_fill.py`, `resolve.py`) and the
  separate local loops. Net: a v2 improvement is written ONCE in JS, both targets get it. The OSS
  `~/life-manager` repo becomes a thin wrapper that vendors/imports the same `lib/`. (The README already
  PROMISED this — "diff isolated to adapters/transport + env"; the impl drifted. #74 makes it true.)
- **#72 — GRAND unification = run ONE OpenClaw app local OR server (Dais's ideal). The single concrete
  blocker (verified 2026-06-21 from the installed plugin SKILL.md):** `@openclaw/voice-call` supports
  Telnyx/Twilio/Plivo BUT only in a TURN-BASED TTS model (initiate_call/speak_to_user/continue_call =
  "say this message, wait for reply"). It has NO realtime full-duplex media bridge. Our product's killer
  feature is the opposite: Telnyx raw RTP (PCMU 8k) ⇄ Gemini Live native-audio (Charon) = a natural,
  barge-in, sub-second conversation (call-bridge.cjs + call-logic.js). Dropping onto OpenClaw as-is would
  regress the magic to a robocall. So #72 path = (1) #74 transport adapter [PREREQUISITE — needed for
  OpenClaw too], (2) upstream call-bridge.cjs into @openclaw/voice-call as a "realtime" provider mode (the
  missing piece), (3) then one OpenClaw agent/skill deploys LOCAL (your Mac, gog, you) OR SERVER (cloud
  box, Composio, Supabase, Stripe, multi-tenant) — same code, different place. NOTE: cloud is NEVER
  "OpenClaw on your Mac" (Mac sleeps, gog is single-account) — cloud = OpenClaw on a SERVER. #74 is step 1
  of this staircase, NOT a throwaway: do #74 now (fix-once, low-risk), launch, then #72 step 2 after.

## Per-user CALL LANGUAGE + identity (2026-06-22, Dais)
- **Language is a USER CHOICE on /lm**, not a phone-country default. New column `lm_users.call_language`
  ('en'|'ja', nullable). A toggle button (**English / 日本語**) on `/lm` persists it. Every call to that user
  uses it from then on — a US phone can pick Japanese, a Japanese phone can pick English.
- **Resolution order at call time:** `lm_users.call_language` → else `langForPhone(phone)` (+81→ja, else en).
  The chosen `lang` is threaded END-TO-END and HMAC-signed: scheduler.js `buildStreamUrl(ev,urgency,lang)` /
  server.js `/test-call` → query `?lang=` (signed with summary|dateTime|location|urgency|lang) → `ctxFromReq`
  verifies → `geminiSetupForEvent(event,urgency,lang)` → `buildCallPrompt(event,urgency,lang,name)`.
- **Identity:** the assistant is the user's **"Life Manager"** and must NEVER call itself "Anicca". It
  **addresses the user BY NAME** in the chosen language (EN: "Hi Daisuke, this is your Life Manager…").
- **Dais's account** (uid `lm_784ad279-4d2c-4274-a318-b51e38285a61`) = `call_language='en'` — the web/cloud
  Life Manager is the one that calls him, and posted transcripts are English.
- We only ever maintain **two** language branches (EN + JA) in `buildCallPrompt`.

## Content account warm-up (@anicca.comedy, 2026-06-22, Dais)
@anicca.comedy is a BRAND-NEW TikTok account → must be **warmed up** before auto-posting. The
life-manager-video pipeline (#45/#50) therefore posts the daily clip as a **DRAFT into the TikTok app
itself** (NOT Postiz `state=PUBLISHED`, NOT the posters app) so Dais warms it by posting manually at first.
Switch to 2×/day auto-publish (verify real POST_ID per post) only AFTER the account is warmed.

## Next bigger version (post-launch)
omni-channel chat (reply to gmail/slack/discord/whatsapp/imessage with approval) · proactive buddy
(lead the user to their best self) · $10k MRR.
