# Life Manager — Cost / Connect / Reliability — Behavioral Spec (VCSDD, lean) — iteration 2

- **Feature**: `life-manager-cost-connect-reliability`
- **Date**: 2026-07-03 (iter-2: addresses adversary iteration-1 FAIL — 11 findings, 3 blockers)
- **Author**: Claude Code (dev IDE, = VCSDD builder) with Dais
- **Status**: Phase 1a rev-2 → resubmit `/vcsdd-spec-review` (iteration-2)
- **Mode**: lean · **Language**: typescript/node (apps/life-call) + Next.js (apps/landing)
- **Code locations + AUTHORITATIVE BRANCH (FIND-005)**: the CANONICAL source = **`origin/main`** (what GHA deploys). All disk-facts in §2 are pinned to `origin/main`; worktrees (e.g. `lipsync-monk`) may diverge and are NOT authoritative. Impl reads/edits `origin/main` `apps/life-call/**` + `apps/landing/**`. Any fact below that differs on `main` at impl time MUST be re-verified against `main` first.

## 0. Adversary iteration-1 resolution map
F1→C1 (one-way default + two-way escalation, drop false "no regression"); F2→C3 (new `lm_route_cache`, not lm_travel_log); F3→moved C7-EXT to `docs/superpowers/specs/2026-07-03-portfolio-self-improve-loop-design.md`; F4→C4 (scheduler selector must include Pipedream users); F5→C5 (single registry = build source too); F6→C5/C6 (debounce + last-good-good guard + one-telegram dedup); F7→OQ2-5 resolved below; F8→C2 (deterministic JP decision + mixed-endpoint branch); F9→Goal1 (in-process ws-not-opened assertion, not billing); F10→moved to portfolio spec + C7 leading-indicator grader; F11→committed transit fixture + Goal5b/Goal7 concrete proofs.

## 0b. Adversary iteration-2 resolution map
FIND-001/002 (gmail): origin/main `ask.js:5-9` = "We NEVER read/send user's Gmail" (asks via Resend our-domain, replies via /telegram + /inbound-email webhooks) → Pipedream = Calendar + gmail.send only, NO gmail read dependency, no CASA (see C4/OQ3). FIND-003 (F4 half): fix BOTH `scheduler.js:42` AND `scheduler.js:280` composio_gcal filters. FIND-004 (/lm bundle): extract STRIPE_LM_URL from the /lm JS CHUNK string (inlined by `force-static` per `page.tsx:10` + `LmClient.tsx:34`, present regardless of ?tg=), not a DOM read. FIND-005: CANONICAL = origin/main (this spec now lives in an origin/main worktree so the adversary reads apps+spec in ONE tree). FIND-006: origin/main WAKE_LEVELS = 2 (T-10/T-5). FIND-007 (address→geo): places/suggest resolves STATIONS not raw JP addresses (verified 0) and Nominatim also fails JP addresses (verified 0), and /plan returns walk journeys even for NYC (verified) → home_address Google-Geocoded ONCE + cached `home_geo`; event geo from ask.js's existing Google-Places grounding; JP decision = deterministic JP bbox on lat/lon (see C2).

## 1. REALITY CHECK (measured 2026-07-03)
- Revenue $0 (Stripe LM subs 0, `lm_stripe_events` 0, `lm_users` 3 = Dais's tests). Pay-link ¥700k→$20/mo bug already FIXED this session (separate hotfix).
- Google bill: **Gemini API dominant** (¥268 on 7/1, Project Anicca/global = voice `gemini-2.5-flash-native-audio-preview-09-2025` ×2/event + flash text) + **Maps Routes Compute Routes Pro** (premium TRAFFIC_AWARE_OPTIMAL). GCP banner: **Gemini keys unrestricted** (security).

## 2. Verified external facts (sources)
| Fact | Source (disk/live) |
|---|---|
| Voice model `gemini-2.5-flash-native-audio-preview-09-2025`, Charon | `apps/life-call/lib/call-logic.js:28` |
| Call TODAY is a **two-way conversation** (VAD + realtimeInput) | `call-logic.js:193-200,378-433` |
| Wake = T-10 firm + T-5 harsh (2 levels, NO T-15) — canonical on **origin/main** `scheduler.js:30-33` (re-verified 2026-07-03 via `git show origin/main`; a 3-level T-15 variant persists in a non-authoritative worktree — worktree name not load-bearing) | `git show origin/main:apps/life-call/scheduler.js` |
| Scheduler selects `calendar_provider=eq.composio_gcal` (hardcoded) | `scheduler.js:42,280` |
| Maps Routes computeRoutes TRAFFIC_AWARE_OPTIMAL + legacy Directions transit | `apps/life-call/lib/travel.js:76,88,119` |
| `lm_travel_log` = dedup/claim ledger `{uid,event_key,leg}`, NO duration/TTL cols | `travel.js:169-177` |
| Stripe link source = build-time env `NEXT_PUBLIC_STRIPE_LM_URL` (GHA secret) | `apps/landing/app/lm/LmClient.tsx:34`; `.github/workflows/netlify-deploy.yml` |
| bare `/lm` = coming-soon gate (no Stripe link); LmClient renders only on `?tg=` | `apps/landing/app/lm/LmBody.tsx:41-63`, `LmClient.tsx` |
| Deploy = GHA (`npm run build` → `netlify deploy --dir=out --no-build --prod`) | `.github/workflows/netlify-deploy.yml` |
| **Free JP transit** `https://api.transit.ls8h.com` (auth-free, CORS, read-only, 748 operators incl JR) — `/api/v1/plan` (time) + `/api/v1/guidance/plan` (route+geometry) + `/api/v1/places/{suggest,reverse}`. ToS: **無償・非公式・無保証**, requires consumer-side "キャッシュ・リトライ・フォールバック・公式誘導", forbids 過度なリクエスト + posing as official. | live-tested; fixtures in `evidence/fixtures/` |
| Free TTS `edge-tts` (MS cloud, no key) — JP Nanami/Keita + EN Guy/Aria tested, μ-law 8k = 78,528 B = 9.816s×8000 exact | live-tested this session |
| Pipedream Connect = one managed OAuth for Calendar + Gmail; `pd` v0.6.1 installed; keys in `~/.openclaw/.env` | installed this session |

## 3. Goal (provable finish line — GLVS)
`done` = **LM per-user monthly Google cost drops from ~$100 to <$10 with the wake call's core guidance preserved, Calendar+Gmail connect through ONE OAuth on Telegram, and a machine continuously verifies+heals the money-path — proven by real side-effect E2E + adversary PASS + my browser/call verification.**

Verifiable conditions:
1. **VOICE (compositional two-way)** — a real answered call is a two-way CONVERSATION produced by the free compositional stack (Groq Whisper STT + Groq Llama LLM + edge-tts TTS); proof = the caller can ask a follow-up and get a spoken answer, AND `live_ws_opened=0` in the app log (Gemini Live native-audio never opened) for that call. Dais hears + converses with the free agent.
2. **ROUTE-JP** — for a JP origin/dest, time+guidance come from `api.transit.ls8h.com` (asserted against the committed fixture), and Google Routes calls for that path = 0 (call-count assertion).
3. **MAPS-CACHE** — provider route calls ≤1 per (uid, event, coarse-time-bucket); a moved event (changed start) recomputes. Asserted by a call-count test.
4. **CONNECT** — a test user connects Calendar AND Gmail-send through ONE Pipedream consent on Telegram; backend reads calendar + sends mail for that user; the scheduler SELECTS that user for wakes.
5. **MONEY-PATH MONITOR** — external check asserts (a) 200 on `/ /life-manager /lm`, (b) STRIPE_LM_URL string-extracted from the /lm JS chunk == registry known-good LM $20/mo link, (c) that Stripe page shows "Life Manager" + "$20". On sustained mismatch (≥2 checks) → auto-rollback + ONE Telegram.
6. **DEPLOY-SAFETY** — GHA post-deploy smoke (5a/5b) auto-restores the previous deploy on failure; proven by injecting a bad build in a preview and observing rollback.
7. **KEY-RESTRICT** — a dedicated LM Gemini key is API-restricted to `generativelanguage.googleapis.com` (+ IP-restricted to Railway egress); proof = `gcloud`/API query of the key's restrictions shows the scope (not merely "banner cleared"). The Live fallback still works (Live = generativelanguage, so the API-restriction does not break it).
8. **SELF-IMPROVE (LM only)** — a daily loop reads LM leading indicators (funnel-step conversion, activation, cost-per-outcome) + writes a persisted report; takes ≥1 action WHEN a non-noise signal exists, else NO-OP (valid). Portfolio-wide version = separate epic.

## 2.1 Non-goals
Portfolio self-improve loop (separate spec). Distribution content specifics. self-funded crypto (colony spec). No X posting.

## 3bis. Behavioral contracts

### C1 — Voice: FREE PIPECAT compositional TWO-WAY CONVERSATIONAL agent (replaces Gemini Live native-audio)
- **ARCHITECTURE PIVOT (Dais 2026-07-04, after 2 independent research passes)**: the LM voice must be a real **two-way CONVERSATION** (listen → understand → respond → the caller can interrupt and continue), like Gemini Live but FREE/cheap and compositional. The earlier one-way clip AND my hand-rolled Node cascade were BOTH wrong: real turn-taking/barge-in is the make-or-break, and hand-rolling it (energyVAD + genId, which the impl adversary FAIL'd on FIND-201) is the trap. **Adopt Pipecat** (BSD, github.com/pipecat-ai/pipecat, native Telnyx serializer) — the researched BP, per HARD #-3 (follow the answer, originality = the bug).
- **STACK** (~$0.01–0.02/min all-in, no idle cost, no Gemini Live; vs Gemini Live's corrected ~$0.023/min): STT = **Groq Whisper Large-v3-Turbo** (`pipecat-ai[groq]`, free tier); LLM = **Groq Llama-3.1-8B-Instant** (`pipecat-ai[groq]`, free tier); TTS = **Kokoro** (`pipecat-ai[kokoro]`, self-hosted, **$0, TRUE streaming, Japanese-confirmed** — replaces edge-tts, which is an unofficial reverse-engineered per-sentence endpoint); **turn-taking = Silero VAD (local, <1ms/30ms chunk) + Smart Turn v3 (`pipecat-ai/smart-turn`, bundled ONNX, $0)** — this is the FREE piece that makes it a conversation, not walkie-talkie (Smart Turn waits for a true end-of-turn, not just silence).
- **INTEGRATION (Pipecat)**: a Pipecat pipeline over Telnyx Media Streaming (μ-law 8k) via Pipecat's built-in `TelnyxFrameSerializer` (docs.pipecat.ai serializers/telnyx = "Built in"). Reference to copy = `pipecat-ai/pipecat-examples/telnyx-chatbot/inbound/bot.py`. Deployment DECISION (OQ7): run the Pipecat pipeline so Telnyx's `stream_url` points at it — either (a) a NEW Python service (Railway) that `dial.js buildStreamUrl` targets, or (b) co-located; the Node service keeps scheduling/dialing/Telegram/Stripe. Pipeline = Telnyx μ-law ↔ [SileroVAD + SmartTurn → Groq Whisper STT → Groq Llama LLM → Kokoro TTS] ↔ Telnyx.
- **BARGE-IN / TURN-TAKING = Pipecat built-in**: Silero VAD + Smart Turn v3 handle end-of-turn + interruption natively (Pipecat cancels the in-flight TTS on user speech and clears the Telnyx queue) — this REPLACES my broken hand-rolled genId/clear logic (FIND-201) with the framework's proven implementation.
- **SUPERSEDES the hand-rolled Node cascade**: `apps/life-call/lib/{compositional-voice,compositional-live,voice-turn,voice-synth}.cjs` + the server.js /ws compositional wiring were the hand-rolled attempt (impl adversary FAIL: FIND-201 barge-in never stops playback, FIND-202 fallbacks unwired). They are REPLACED by the Pipecat pipeline. (voice-cheap.js already deleted.) Keep only what Pipecat doesn't provide.
- **GEMINI LIVE FULLY REMOVED**: no `openGeminiLive`, no `new WebSocket(geminiLiveWsUrl)` on the call path. `live_ws_opened=0` structurally. Gemini Live only behind an OFF-by-default emergency flag, logged.
- **IN**: an answered call (uid, event, urgency, route/leave-time, call_language) — the agent OPENS with the wake guidance (route INCLUDED, FIND-203), then converses.
- **OUT**: a real two-way phone conversation (STT→LLM→TTS with Silero+SmartTurn turn-taking + barge-in).
- **FALLBACKS (fail-closed, FIND-202)**: within Pipecat's service layer — STT Groq→Deepgram/faster-whisper; LLM Groq→Cerebras(free)/Gemini-Flash-text; TTS Kokoro→Piper. Covers no-key/401/403/429/timeout. NEVER re-opens Gemini Live; never a silent call.
- **DTMF (FIND-104)**: a keypress no longer opens Gemini Live (the old `server.js:447` trigger is deleted). In the compositional loop DTMF is logged and otherwise ignored (or reserved as an explicit end-call signal) — never an escalation to paid Live.
- **TTS STREAMING + LATENCY (FIND-003)**: TTS is `python3 -m edge_tts` invoked **per SENTENCE** as the LLM streams (not once on the full response) to cut time-to-first-audio; per-call `mkdtemp`. The ~500–800 ms/turn is Pipecat's cascaded BASELINE = a MEASURED impl target (Phase-1b), not a guarantee. NOTE: `package.json` currently lists an unused `msedge-tts` Node dep — it returned 0 bytes / no RAW-PCM in testing, so it is NOT used; remove it (dead dep) during impl.
- **QUALITY BAR**: the agent opens by naming event + place + route + urgency in call_language, then answers the caller's questions in a natural back-and-forth.

### C2 — Routing: JP via transit.ls8h.com, else Google (F8 + ToS)
- **ADDRESS→GEO (corrected per iter-3 FIND-003 + my live tests)**: transit `/api/v1/places/suggest` resolves STATIONS/landmarks ("新宿駅"→geo, verified) but NOT raw JP postal addresses ("新宿区南元町15-27"→0, verified); OSM Nominatim also fails those JP addresses (verified 0). So geo is obtained the way the code ALREADY does it: `home_address` is geocoded ONCE (Google Geocoding) and cached as `home_geo` on `lm_users` (one-time per user = negligible cost, NOT the $100 driver); event geos already come from ask.js's existing Google-Places grounding (`ask.js` RESOLVE). The cost cut is on ROUTING (Routes Compute Pro premium, per-tick), not on one-time geocoding.
- **JP decision = DETERMINISTIC JP bounding-box on resolved lat/lon (not places/suggest, not plan-journeys)**: `/plan` returns walk-only journeys even for NYC (verified journeys=1), so "0 journeys" does NOT mean non-JP. Use a JP bbox (lat 24–46, lon 122–146) on both resolved geos: both in-bbox → JP transit routing via `/api/v1/plan` (+`/guidance/plan`); else → Google Routes. Bbox on lat/lon = parsing, not judgment.
- **MIXED/UNRESOLVABLE / transit 0-journeys / non-200 / timeout**: → Google Routes for the WHOLE request (per ToS: cache+retry+fallback mandatory).
- **OUT**: `{durationSecs, legs[], guidance}`; JP → `/api/v1/plan` (+ `/api/v1/guidance/plan` for the "how to get there" line); else Google.
- **EDGE/ERROR**: transit 0 journeys OR non-200 OR timeout → Google fallback, log. Per ToS: cache + retry + fallback are MANDATORY; the product must not present transit output as official (it's 非公式・無保証) — for a phone guidance line that's acceptable (advisory, not authoritative).
- **INVARIANT**: no key/secret sent to transit (auth-free); no 過度なリクエスト (guaranteed by C3 cache).

### C3 — Route cache = NEW store `lm_route_cache` (F2)
- **NOT** `lm_travel_log` (that stays a dedup/claim ledger). New table/columns: `(uid, from_geo, to_geo, time_bucket, provider, duration_secs, geometry, computed_at, ttl)` + migration.
- **IN**: route request (uid, from, to, time-bucket). **OUT**: cached row within TTL, else compute-once + store.
- **INVARIANT**: for a given (uid, event, coarse-time-bucket) external providers are called ≤1×. TTL + bucket sized so a moved event (start changed → new bucket) recomputes; stale traffic beyond TTL recomputes.

### C4 — Connect: ONE Pipedream consent (Calendar + Gmail-send); Telegram-only; scheduler must select Pipedream users (F4)
- **DECISION**: Telegram (@LifeManagerBotbot) = sole onboarding; web `/lm` stays gated. One Pipedream Connect consent grants **Calendar + Gmail-send** → re-adds Gmail with **one fewer** onboarding step.
- **GMAIL SCOPE (OQ3, re-corrected against origin/main truth)**: on **origin/main**, `ask.js:1-9` states verbatim "We NEVER read or send from the user's Gmail" — asks go out from OUR domain (Resend, Reply-To `reply+<token>@reply.aniccaai.com`) and REPLIES arrive on webhooks (`/telegram`, `/inbound-email`); there is NO user-Gmail read on the canonical path. (`mail-gog.js`/`mail-unipile.js` `listInbox` DO exist on origin/main but are DEAD CODE — `ask.js:18` imports only `getCalendar`, never `getMail`; grep confirms the only caller is a test. The adversary iter-2 FIND-001 mistook this dead code for a live read path.) → Pipedream grants **Calendar + `gmail.send`** only; NO `gmail.readonly`, NO CASA, and NO Gmail-read dependency to break. gmail.send is used for late-notice mail; asks/replies stay on Resend+webhooks.
- **MIGRATION (F4, corrected per FIND-003)**: BOTH selector sites hardcode `calendar_provider=eq.composio_gcal` — `scheduler.js:42` (batch scan) AND `getUserByUid` `scheduler.js:280` (Inngest per-user refetch behind wakeUserOnce/travelUserOnce/askUserOnce). BOTH must widen to `in.(composio_gcal,pipedream_gcal)`, else a Pipedream user is picked in the batch but re-excluded on refetch. Dual-read until Composio users migrate.
- **EDGE**: partial grant (calendar but not gmail) → onboarding reflects true state; never claim gmail if absent.
- **INVARIANT**: no RESTRICTED scope; secrets never logged.
- **TELEGRAM FLOW**: /start → name → phone → ONE tap Connect Google (Cal+Gmail) → ONE tap Subscribe $20/mo → done.

### C5 — Money-path monitor + single SSOT (F5, F6)
- **SSOT (F5)**: the known-good LM Stripe link lives in ONE registry file `apps/landing/monitors/registry.json`. The build MUST read the link from that same registry (or the monitor additionally asserts `GHA secret NEXT_PUBLIC_STRIPE_LM_URL == registry.stripe_lm_url`) so build-source and monitor-source cannot diverge.
- **CHECK (corrected per FIND-004)**: (a) 200 on `/ /life-manager /lm`; (b) STRIPE_LM_URL extracted from the **/lm page's JS chunk** (bundle-level string match on `buy.stripe.com/<slug>` — proven method: the value is inlined at build via `force-static`, so it is present in the chunk regardless of `?tg=`; this is a chunk-string read, NOT a DOM read which would need full Google OAuth) == `registry.stripe_lm_url`; (c) fetch that Stripe link and assert the page contains "Life Manager" + "$20".
- **EDGE (F6)**: rollback requires **≥2 consecutive FAILs** (debounce, no single-transient rollback); before switching, the rollback target MUST itself pass (a)+(b)+(c) — if no recent deploy passes → escalate, do NOT rollback into another bad build (flap guard); Telegram escalation is **deduped** (one message per incident, state flag cleared on recovery).
- **INVARIANT (SRE)**: black-box + content assertion (200 ≠ enough); low-noise (page only on a real, ongoing symptom).

### C6 — Deploy smoke + rollback host (OQ4)
- GHA `netlify-deploy.yml` runs a post-deploy smoke (C5 a/b) after `netlify deploy --prod`; on failure it restores the previous deploy (`deploys/<last-good>/restore`) — with the same last-good-good guard as C5.
- **MONITOR HOST (OQ4 re-resolved per project rule + FIND-104)**: the 15-min money-path monitor runs as an **OpenClaw cron** (`~/.openclaw/cron/jobs.json`, deterministic node command, no LLM) — NOT a GitHub Actions scheduled workflow, because the project rule forbids new scheduled GHA workflows (only `netlify-deploy.yml` may exist; cron is canonical in OpenClaw). OpenClaw runs on the Mac Mini = independent of Railway/Netlify, so it still satisfies 'the monitor must not die with the monitored'. Runnable = `apps/landing/scripts/money-path-monitor.mjs` (uses the tested RollbackController; state persists across runs).

### C7 — Self-improve loop (LM only) (F10)
- **IN** daily tick. **OUT** LM metrics snapshot + report; ≥1 action when a non-noise signal exists.
- **GRADER at $0 (F10)**: do NOT gate on MRR-delta (noise at N=3); fitness = LEADING indicators (funnel-step conversion, activation, cost-per-outcome). NO-OP is valid when even leading signal is absent (reconciles Goal 8 with rule-5). Portfolio version = separate epic.
- **INVARIANT**: every action verified by real side-effect; no X; human only on a single escalation channel.

## 4. Verification architecture (Phase 1b seed)
- **RED (node --test, real fixtures)** — C1 (highest-risk contract) unit set: **C1 VAD endpointing** (energy+silence threshold → utterance boundaries on a fixture PCM buffer), **C1 sentence-splitter** (LLM token stream → sentence chunks fed to TTS), **C1 barge-in state machine** (speech-start while speaking → stop outbound send + drop buffer; no Live opened), **C1 Groq request builders** (STT multipart + LLM chat body shapes), **C1 fail-closed** (no GROQ_API_KEY → local fallbacks chosen, `openGeminiLive` never called), **C1 live_ws_opened=0** on the normal path (incl. DTMF no longer opens Live). Plus: C2 parse against `evidence/fixtures/transit-plan-*.json` + `guidance-*.json`; C2 JP-bounds/resolvability + mixed-endpoint fallback; C3 cache call-count + moved-event invalidation; C1 fallback ordering + "ws-not-opened on default" counter; C5 assertion logic (bundle string → detect wrong/right link) + debounce + flap-guard + telegram-dedup; C6 rollback trigger.
- **NO-MOCK E2E (mine, after adversary PASS)**: real wake call on cheap path (hear it + Live-counter=0); money-path monitor vs live prod; Pipedream test-connect (cal+gmail) + confirm scheduler selects the user; `gcloud` key-restriction query.

## 5. Open questions — RESOLVED in-spec (F7)
- **OQ1 (voice architecture)**: RESOLVED (redesigned 2026-07-04 per Dais) — FREE COMPOSITIONAL two-way agent (Groq Whisper STT + Groq Llama LLM + edge-tts TTS) replacing Gemini Live native-audio; edge-tts (JP+EN, μ-law 8k) is the TTS stage only, synthesized per-sentence during the LLM stream. The prior 'pre-synthesized one-way clip' is SUPERSEDED (it was not a conversation). See C1.
- **OQ2 (transit ToS/coverage/limits)**: RESOLVED — free, unofficial, no SLA; ToS REQUIRES consumer-side cache+retry+fallback+official-redirect and forbids excessive requests/posing-as-official → satisfied by C3 cache + C2 Google fallback + advisory framing. Coverage = 748 operators incl JR East (broad JP). Non-JP/rural → Google.
- **OQ3 (Pipedream Gmail scope vs CASA)**: RESOLVED (corrected) — Pipedream grants Calendar + `gmail.send` only (sensitive, not RESTRICTED → no CASA). Gmail-READ (ask/notify's `mail-gog gmail search`) is NOT migrated to Pipedream and is OUT OF SCOPE; it stays on the existing provider; Telegram-first users get location-reply reads via Telegram. No `gmail.readonly`, no CASA trap.
- **OQ4 (monitor host)**: RESOLVED (corrected FIND-104) — OpenClaw cron (`~/.openclaw/cron/jobs.json`) running `apps/landing/scripts/money-path-monitor.mjs` every 15 min; NOT a GHA scheduled workflow (project rule forbids it). OpenClaw on the Mac Mini is independent of Railway/Netlify.
- **OQ6 (GROQ_API_KEY provisioning + fail-closed, FIND-004)**: `GROQ_API_KEY` is NOT yet in `~/.openclaw/.env` (0 refs). Impl MUST provision a Groq free-tier key (Groq console signup via CloakBrowser/Google login) and store it in `~/.openclaw/.env` + Railway env. FAIL-CLOSED: if the key is absent/unauthorized at runtime, the voice loop runs on the LOCAL fallbacks (faster-whisper + Gemini-Flash-text + edge-tts), and MUST NOT re-open Gemini Live native-audio. (Parallels OQ5's Gemini-key treatment.)
- **OQ5 (key restriction vs Live fallback)**: RESOLVED — dedicated LM key restricted to `generativelanguage.googleapis.com` (+ Railway IP); the Live fallback is also generativelanguage → restriction does not break it. Enumerate other consumers of the old key before rotating.
