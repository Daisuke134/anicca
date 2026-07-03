# Life Manager — Cost / Connect / Reliability — Behavioral Spec (VCSDD, lean) — iteration 3

- **Feature**: `life-manager-cost-connect-reliability`
- **Date**: 2026-07-04 (iter-3: **VOICE SIMPLIFIED** — keep Gemini Live, shelve Pipecat/Kokoro; the $100 was Maps, already fixed)
- **Author**: Claude Code (dev IDE, = VCSDD builder) with Dais
- **Status**: Phase 1a rev-3 → resubmit `/vcsdd-spec-review` (iteration-3)
- **Mode**: lean · **Language**: typescript/node (apps/life-call) + Next.js (apps/landing)
- **Code locations + AUTHORITATIVE BRANCH (FIND-005)**: the CANONICAL source = **`origin/main`** (what GHA deploys). All disk-facts in §2 are pinned to `origin/main`; worktrees (e.g. `lipsync-monk`) may diverge and are NOT authoritative. Impl reads/edits `origin/main` `apps/life-call/**` + `apps/landing/**`. Any fact below that differs on `main` at impl time MUST be re-verified against `main` first.

## 0c. iteration-3 DECISION (Dais 2026-07-04) — the SIMPLE truth about the cost
The June ~$100 Google bill was **88% Maps (Routes Compute Pro, uncached per-tick)** and only **~12% (~$11/mo) Gemini voice** — measured. **The cost problem is MAPS, and C2 (JP free transit) + C3 (route cache) already fix it.** Therefore **voice does NOT need re-architecting**: the existing **Gemini Live native-audio call is ALREADY a two-way conversation, already works, and is now cheap** (~$11/mo after the Maps fix). We KEEP it. The Pipecat/Kokoro/Groq free-voice stack (`apps/life-voice/`) is **SHELVED** — kept in the repo as a verified-but-dormant future scale-time option (revisit only when voice minutes make Gemini voice actually hurt), OFF the call path, tested but not wired. This REVERSES iter-2's C1 voice pivot. Rationale = Anthropic BP "start simple; add complexity only when simpler solutions fall short" + don't build a whole new service to save ~$11/mo. What we DO delete = the broken hand-rolled Node cascade (never worked).

## 0. Adversary iteration-1 resolution map
F1→C1 (one-way default + two-way escalation, drop false "no regression"); F2→C3 (new `lm_route_cache`, not lm_travel_log); F3→moved C7-EXT to `docs/superpowers/specs/2026-07-03-portfolio-self-improve-loop-design.md`; F4→C4 (scheduler selector must include Pipedream users); F5→C5 (single registry = build source too); F6→C5/C6 (debounce + last-good-good guard + one-telegram dedup); F7→OQ2-5 resolved below; F8→C2 (deterministic JP decision + mixed-endpoint branch); F9→Goal1 (in-process ws-not-opened assertion, not billing); F10→moved to portfolio spec + C7 leading-indicator grader; F11→committed transit fixture + Goal5b/Goal7 concrete proofs.

## 0b. Adversary iteration-2 resolution map
FIND-001/002 (gmail): origin/main `ask.js:5-9` = "We NEVER read/send user's Gmail" (asks via Resend our-domain, replies via /telegram + /inbound-email webhooks) → Pipedream = Calendar + gmail.send only, NO gmail read dependency, no CASA (see C4/OQ3). FIND-003 (F4 half): fix BOTH `scheduler.js:42` AND `scheduler.js:280` composio_gcal filters. FIND-004 (/lm bundle): extract STRIPE_LM_URL from the /lm JS CHUNK string (inlined by `force-static` per `page.tsx:10` + `LmClient.tsx:34`, present regardless of ?tg=), not a DOM read. FIND-005: CANONICAL = origin/main (this spec now lives in an origin/main worktree so the adversary reads apps+spec in ONE tree). FIND-006: origin/main WAKE_LEVELS = 2 (T-10/T-5). FIND-007 (address→geo): places/suggest resolves STATIONS not raw JP addresses (verified 0) and Nominatim also fails JP addresses (verified 0), and /plan returns walk journeys even for NYC (verified) → home_address Google-Geocoded ONCE + cached `home_geo`; event geo from ask.js's existing Google-Places grounding; JP decision = deterministic JP bbox on lat/lon (see C2).

## 1. REALITY CHECK (measured 2026-07-03)
- Revenue $0 (Stripe LM subs 0, `lm_stripe_events` 0, `lm_users` 3 = Dais's tests). Pay-link ¥700k→$20/mo bug already FIXED this session (separate hotfix).
- Google bill: **Maps Routes Compute Routes Pro = the ~88% driver** (premium TRAFFIC_AWARE_OPTIMAL, recomputed every scheduler tick, uncached — this is the ~$100). **Gemini voice `gemini-2.5-flash-native-audio-preview-09-2025` = only ~12% (~$11/mo)** (¥268 on 7/1, ×2/event + flash text). GCP banner: **Gemini keys unrestricted** (security). ⇒ the fix is Maps (C2+C3); voice is left as-is.

## 2. Verified external facts (sources)
| Fact | Source (disk/live) |
|---|---|
| Voice model `gemini-2.5-flash-native-audio-preview-09-2025`, Charon | `apps/life-call/lib/call-logic.js:28` |
| Call TODAY is a **two-way conversation** (VAD + realtimeInput) — this is KEPT | `call-logic.js:193-200,378-433` |
| Wake = T-10 firm + T-5 harsh (2 levels, NO T-15) — canonical on **origin/main** `scheduler.js:30-33` (re-verified 2026-07-03 via `git show origin/main`; a 3-level T-15 variant persists in a non-authoritative worktree — worktree name not load-bearing) | `git show origin/main:apps/life-call/scheduler.js` |
| Scheduler selects `calendar_provider=eq.composio_gcal` (hardcoded) | `scheduler.js:42,280` |
| Maps Routes computeRoutes TRAFFIC_AWARE_OPTIMAL + legacy Directions transit | `apps/life-call/lib/travel.js:76,88,119` |
| `lm_travel_log` = dedup/claim ledger `{uid,event_key,leg}`, NO duration/TTL cols | `travel.js:169-177` |
| Stripe link source = build-time env `NEXT_PUBLIC_STRIPE_LM_URL` (GHA secret) | `apps/landing/app/lm/LmClient.tsx:34`; `.github/workflows/netlify-deploy.yml` |
| bare `/lm` = coming-soon gate (no Stripe link); LmClient renders only on `?tg=` | `apps/landing/app/lm/LmBody.tsx:41-63`, `LmClient.tsx` |
| Deploy = GHA (`npm run build` → `netlify deploy --dir=out --no-build --prod`) | `.github/workflows/netlify-deploy.yml` |
| **Free JP transit** `https://api.transit.ls8h.com` (auth-free, CORS, read-only, 748 operators incl JR) — `/api/v1/plan` (time) + `/api/v1/guidance/plan` (route+geometry) + `/api/v1/places/{suggest,reverse}`. ToS: **無償・非公式・無保証**, requires consumer-side "キャッシュ・リトライ・フォールバック・公式誘導", forbids 過度なリクエスト + posing as official. | live-tested; fixtures in `evidence/fixtures/` |
| Pipedream Connect = one managed OAuth for Calendar + Gmail; `pd` v0.6.1 installed; keys in `~/.openclaw/.env` | installed this session |
| `apps/life-voice/` Pipecat scaffold (Groq STT/LLM + Kokoro TTS + Silero/SmartTurn) EXISTS + imports verified against pipecat 1.4.0, OQ9 HMAC parity proven — but **SHELVED, not on the call path** (needs system espeak-ng + Railway deploy + PUBLIC_WSS cutover to activate; future epic) | this session |

## 3. Goal (provable finish line — GLVS)
`done` = **LM per-user monthly Google cost drops from ~$100 to <$10 with the wake call's core guidance preserved, Calendar+Gmail connect through ONE OAuth on Telegram, and a machine continuously verifies+heals the money-path — proven by real side-effect E2E + adversary PASS + my browser/call verification.**

Verifiable conditions:
1. **VOICE (keep Gemini Live)** — a real answered call is a two-way CONVERSATION on the EXISTING Gemini Live native-audio path (`call-logic.js` Charon, already VAD + realtimeInput); proof = the caller asks a follow-up and gets a spoken answer + can interrupt (barge-in). NO voice re-architecture. The dead hand-rolled Node cascade is DELETED; `apps/life-voice` (Pipecat) stays shelved/unwired. Dais hears + converses + interrupts on the current stack.
2. **ROUTE-JP** — for a JP origin/dest, time+guidance come from `api.transit.ls8h.com` (asserted against the committed fixture), and Google Routes calls for that path = 0 (call-count assertion).
3. **MAPS-CACHE** — provider route calls ≤1 per (uid, event, coarse-time-bucket); a moved event (changed start) recomputes. Asserted by a call-count test.
4. **CONNECT** — a test user connects Calendar AND Gmail-send through ONE Pipedream consent on Telegram; backend reads calendar + sends mail for that user; the scheduler SELECTS that user for wakes.
5. **MONEY-PATH MONITOR** — external check asserts (a) 200 on `/ /life-manager /lm`, (b) STRIPE_LM_URL string-extracted from the /lm JS chunk == registry known-good LM $20/mo link, (c) that Stripe page shows "Life Manager" + "$20". On sustained mismatch (≥2 checks) → auto-rollback + ONE Telegram.
6. **DEPLOY-SAFETY** — GHA post-deploy smoke (5a/5b) auto-restores the previous deploy on failure; proven by injecting a bad build in a preview and observing rollback.
7. **KEY-RESTRICT** — a dedicated LM Gemini key is API-restricted to `generativelanguage.googleapis.com` (+ IP-restricted to Railway egress); proof = `gcloud`/API query of the key's restrictions shows the scope (not merely "banner cleared"). Gemini Live (voice) still works (Live = generativelanguage, so the API-restriction does not break it).
8. **SELF-IMPROVE (LM only)** — a daily loop reads LM leading indicators (funnel-step conversion, activation, cost-per-outcome) + writes a persisted report; takes ≥1 action WHEN a non-noise signal exists, else NO-OP (valid). Portfolio-wide version = separate epic.

## 2.1 Non-goals
Portfolio self-improve loop (separate spec). Distribution content specifics. self-funded crypto (colony spec). No X posting. **Free/compositional voice re-architecture (Pipecat/Kokoro) = future scale-time epic, NOT this iteration.**

## 3bis. Behavioral contracts

### C1 — Voice: KEEP the existing Gemini Live native-audio two-way call (NO re-architecture)
- **DECISION (Dais 2026-07-04, reverses iter-2's Pipecat pivot)**: the LM voice **stays on the existing Gemini Live native-audio path** — it is ALREADY a two-way conversation, already works, and is now cheap (~$11/mo, ~12% of the bill) once C2/C3 kill the Maps cost. Do NOT rebuild voice. Anthropic BP: "start with the simplest thing; add complexity only when simpler solutions fall short." A whole new Python service to shave ~$11/mo, with 0 paying users, is over-engineering.
- **IN SCOPE for C1 = cleanup only, no new voice engine**:
  1. **DELETE the broken hand-rolled Node cascade** (never worked — impl adversary FAIL FIND-201/202): `apps/life-call/lib/{compositional-voice,compositional-live,voice-turn,voice-synth}.cjs` + their tests + the `server.js` `/ws` `createConversation` wiring that routed to it. Restore the Gemini Live `/ws` bridge as the sole call path. (`voice-cheap.js` already gone.)
  2. **CONFIRM the Gemini Live path still dials + converses** end-to-end after the cleanup (real call to Dais; caller speaks → Charon answers → barge-in works).
- **SHELVED (not deleted, not wired)**: `apps/life-voice/` (Pipecat + Groq + Kokoro) stays in the repo as a verified-but-dormant future option for when voice minutes make Gemini voice expensive at scale. It is NOT on the call path; Telnyx `stream_url` keeps pointing at the Gemini Live bridge. `GROQ_API_KEY` stays provisioned (harmless). Re-activating it later = a separate epic (would then need: system espeak-ng in the image, Railway deploy, PUBLIC_WSS cutover, an OQ8 latency gate). Documented so we don't re-derive it.
- **COST FRAME**: Gemini Live native-audio ≈ $0.023/min; a wake call ~1–2 min; at current volume ≈ $11/mo — acceptable. The real cut is C2+C3 (Maps).
- **IN**: an answered call (uid, event, urgency, route/leave-time, call_language) — Gemini Live opens with the wake guidance (route INCLUDED), then converses (existing behavior).
- **OUT**: a real two-way phone conversation on Gemini Live (unchanged behavior), MINUS the dead hand-rolled cascade.
- **DTMF**: keep whatever the origin/main Gemini Live path already does; the cleanup only removes the cascade, not existing Gemini behavior.
- **INVARIANT**: after cleanup, exactly ONE voice path is live (Gemini Live); the dead cascade files are gone; `apps/life-voice` imports cleanly but nothing dials into it; no silent call regression.

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
- **RED — C1 (voice cleanup, Node)**: after deleting the cascade, (a) `apps/life-call` still boots + the `/ws` handler routes to the Gemini Live bridge (not to a now-deleted `createConversation`); (b) grep proves `compositional-*.cjs`/`voice-turn.cjs`/`voice-synth.cjs` are GONE and nothing imports them; (c) the Gemini Live path is intact (call-logic.js unchanged). NO new Python pipeline to test (life-voice is shelved). Plus: C2 parse against `evidence/fixtures/transit-plan-*.json` + `guidance-*.json`; C2 JP-bounds/resolvability + mixed-endpoint fallback; C3 cache call-count + moved-event invalidation; C5 assertion logic (bundle string → detect wrong/right link) + debounce + flap-guard + telegram-dedup; C6 rollback trigger.
- **NO-MOCK E2E (mine, after adversary PASS)**: real wake call on the Gemini Live path (Dais hears + converses + interrupts); money-path monitor vs live prod; Pipedream test-connect (cal+gmail) + confirm scheduler selects the user; `gcloud` key-restriction query.

## 5. Open questions — RESOLVED in-spec (F7)
- **OQ1 (voice architecture)**: RESOLVED (iter-3, Dais 2026-07-04) — **KEEP Gemini Live native-audio** (already two-way, already works, ~$11/mo after the Maps fix). No re-architecture. The Pipecat/Kokoro stack is shelved (see C1 + OQ7/OQ8). This reverses iter-2's pivot.
- **OQ2 (transit ToS/coverage/limits)**: RESOLVED — free, unofficial, no SLA; ToS REQUIRES consumer-side cache+retry+fallback+official-redirect and forbids excessive requests/posing-as-official → satisfied by C3 cache + C2 Google fallback + advisory framing. Coverage = 748 operators incl JR East (broad JP). Non-JP/rural → Google.
- **OQ3 (Pipedream Gmail scope vs CASA)**: RESOLVED (corrected) — Pipedream grants Calendar + `gmail.send` only (sensitive, not RESTRICTED → no CASA). Gmail-READ is NOT migrated and is OUT OF SCOPE; it stays on the existing provider; Telegram-first users get location-reply reads via Telegram. No `gmail.readonly`, no CASA trap.
- **OQ4 (monitor host)**: RESOLVED (corrected FIND-104) — OpenClaw cron (`~/.openclaw/cron/jobs.json`) running `apps/landing/scripts/money-path-monitor.mjs` every 15 min; NOT a GHA scheduled workflow (project rule forbids it). OpenClaw on the Mac Mini is independent of Railway/Netlify.
- **OQ6 (GROQ_API_KEY)**: RESOLVED — provisioned (free-tier, in `~/.openclaw/.env` + Railway; STT+LLM live-verified 2026-07-04). Now UNUSED on the live path (voice = Gemini Live); kept for the shelved life-voice option. No fail-closed voice-fallback logic needed this iteration (Gemini Live is the path).
- **OQ7 (Node vs Python service split)**: RESOLVED (iter-3) — NO split this iteration. Voice stays in the Node `apps/life-call` Gemini Live bridge. `apps/life-voice/` (Python Pipecat) exists but is SHELVED/unwired. If reactivated later, `scheduler.js buildStreamUrl` (env `PUBLIC_WSS`) would point Telnyx `stream_url` at it — a future epic.
- **OQ8 (Kokoro footprint / TTS latency)**: RESOLVED (iter-3) — MOOT this iteration (no Kokoro on the live path). Findings recorded for the future epic: Kokoro model auto-downloads; it needs **system espeak-ng** in the image (else JA/EN phonemization crashes — proven this session on Mac; fix = `apt-get install espeak-ng`); a target-CPU latency gate (~800ms budget, Piper fallback) would block that future ship. Not a blocker now.
- **OQ9 (HMAC auth carryover)**: RESOLVED-as-requirement (for the future life-voice epic) — proven this session that Node `signCtx` (HMAC over [summary,dateTime,location,urgency,lang,name] with `LM_CALL_SECRET`, base64url) and the Python `server.py verify_ctx` agree (valid accepted, tampered/nosig rejected). MOOT for the live path (Gemini Live bridge already does its own uid-sig check).
- **OQ5 (key restriction vs Live fallback)**: RESOLVED — dedicated LM key restricted to `generativelanguage.googleapis.com` (+ Railway IP); Gemini Live (voice) is also generativelanguage → restriction does not break it. Enumerate other consumers of the old key before rotating.
