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

## Next bigger version (post-launch)
omni-channel chat (reply to gmail/slack/discord/whatsapp/imessage with approval) · proactive buddy
(lead the user to their best self) · $10k MRR.
