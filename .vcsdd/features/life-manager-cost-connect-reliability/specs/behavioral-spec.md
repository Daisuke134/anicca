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
FIND-001/002 (major, gmail read)→C4/OQ3: dropped the false "reply-by-email never read Gmail" claim; Pipedream=Calendar+gmail.send only; Gmail-READ stays on existing provider, OUT OF SCOPE; TG users reply via Telegram. FIND-003 (major, F4 half)→C4: fix BOTH `scheduler.js:42` AND `getUserByUid` `scheduler.js:271`. FIND-004 (major, /lm bundle)→C5/Goal5: extract STRIPE_LM_URL from the /lm JS CHUNK string (inlined by force-static, present regardless of ?tg=), not a DOM/?tg= read. FIND-005 (minor, branch)→pinned CANONICAL=origin/main. FIND-006 (minor, wake levels)→re-verified origin/main = T-10+T-5 (2 levels); 3-level variant is stale worktree only. FIND-007 (major, address→geo)→C2: resolve address via transit `/api/v1/places/suggest` (free JP geocode + resolvability probe), non-circular, no Google Geocoding.

## 1. REALITY CHECK (measured 2026-07-03)
- Revenue $0 (Stripe LM subs 0, `lm_stripe_events` 0, `lm_users` 3 = Dais's tests). Pay-link ¥700k→$20/mo bug already FIXED this session (separate hotfix).
- Google bill: **Gemini API dominant** (¥268 on 7/1, Project Anicca/global = voice `gemini-2.5-flash-native-audio-preview-09-2025` ×2/event + flash text) + **Maps Routes Compute Routes Pro** (premium TRAFFIC_AWARE_OPTIMAL). GCP banner: **Gemini keys unrestricted** (security).

## 2. Verified external facts (sources)
| Fact | Source (disk/live) |
|---|---|
| Voice model `gemini-2.5-flash-native-audio-preview-09-2025`, Charon | `apps/life-call/lib/call-logic.js:28` |
| Call TODAY is a **two-way conversation** (VAD + realtimeInput) | `call-logic.js:193-200,378-433` |
| Wake = T-10 firm + T-5 harsh (2 levels, NO T-15) — canonical on **origin/main** `scheduler.js:30-33` (re-verified 2026-07-03; the 3-level T-15 variant exists only in the stale `lipsync-monk` worktree, non-authoritative per FIND-006) | `git show origin/main:apps/life-call/scheduler.js` |
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
1. **VOICE-COST** — a real wake call plays the cheap one-way path; proof = **in-process assertion the Gemini Live websocket is never opened on the default path** (a Live-session counter + native-audio-token counter in the app log = 0 for that call), NOT GCP billing. Dais hears the call.
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

### C1 — Voice: cheap ONE-WAY default + two-way ESCALATION (F1)
- **SCOPE CHANGE (explicit, not "no regression")**: today's call is a full two-way Gemini-Live conversation; the default becomes a **pre-synthesized ONE-WAY guidance clip** (cheap-text line → edge-tts → μ-law → Telnyx `play`). This is a deliberate capability reduction for the common case (a wake call is "leave now, go via X").
- **TWO-WAY ESCALATION**: if VAD detects the caller speaking (or a keypad request), OPEN a Gemini Live session for interactive Q&A (billed, rare, logged as `voice_mode=live_escalation`). So "give directions on demand" is preserved via escalation, not the default.
- **IN**: due wake (uid, event, urgency, resolved route/leave-time, call_language).
- **OUT**: a phone call whose default audio is the one-way clip; on caller interaction → Live Q&A.
- **EDGE/ERROR**: TTS fail → next provider (edge-tts → local Kokoro/piper) → last resort Live; if NO audio → do NOT dial (silent call worse than none), log+count.
- **INVARIANT (measurable)**: on the default path the Gemini Live ws is NEVER opened (counter=0) → zero native-audio tokens. Live only on explicit escalation.
- **QUALITY BAR**: the one-way clip names event + place + route + urgency in call_language.

### C2 — Routing: JP via transit.ls8h.com, else Google (F8 + ToS)
- **ADDRESS→GEO + JP decision (FIND-007, deterministic, no LLM, no Google Geocoding)**: inputs are ADDRESS STRINGS (`home_address` e.g. "新宿区南元町15-27") + event locations, not lat/lon. Resolve each with the transit API's OWN free `/api/v1/places/suggest` (+ `/places/reverse`). This single call is BOTH the free JP geocoder AND the JP-resolvability probe: if an address resolves to a JP place/station in the feed → JP transit path; if it does NOT resolve → Google fallback (which geocodes internally). No standalone Google Geocoding call is introduced; the gate is non-circular (one free resolve step, then branch).
- **MIXED/UNRESOLVABLE**: if either endpoint fails to resolve in the transit feed (non-JP, rural, or unknown) → Google for the WHOLE request.
- **OUT**: `{durationSecs, legs[], guidance}`; JP → `/api/v1/plan` (+ `/api/v1/guidance/plan` for the "how to get there" line); else Google.
- **EDGE/ERROR**: transit 0 journeys OR non-200 OR timeout → Google fallback, log. Per ToS: cache + retry + fallback are MANDATORY; the product must not present transit output as official (it's 非公式・無保証) — for a phone guidance line that's acceptable (advisory, not authoritative).
- **INVARIANT**: no key/secret sent to transit (auth-free); no 過度なリクエスト (guaranteed by C3 cache).

### C3 — Route cache = NEW store `lm_route_cache` (F2)
- **NOT** `lm_travel_log` (that stays a dedup/claim ledger). New table/columns: `(uid, from_geo, to_geo, time_bucket, provider, duration_secs, geometry, computed_at, ttl)` + migration.
- **IN**: route request (uid, from, to, time-bucket). **OUT**: cached row within TTL, else compute-once + store.
- **INVARIANT**: for a given (uid, event, coarse-time-bucket) external providers are called ≤1×. TTL + bucket sized so a moved event (start changed → new bucket) recomputes; stale traffic beyond TTL recomputes.

### C4 — Connect: ONE Pipedream consent (Calendar + Gmail-send); Telegram-only; scheduler must select Pipedream users (F4)
- **DECISION**: Telegram (@LifeManagerBotbot) = sole onboarding; web `/lm` stays gated. One Pipedream Connect consent grants **Calendar + Gmail-send** → re-adds Gmail with **one fewer** onboarding step.
- **GMAIL SCOPE (OQ3, corrected per FIND-001/002)**: Pipedream grants **Calendar + `gmail.send`** (sensitive, not RESTRICTED → no CASA). The Gmail-**READ** used TODAY by ask/notify (`lib/transport/mail-gog.js:31-37` `gmail search newer_than:2d`; `ask.js`) is a SEPARATE capability — this feature does NOT migrate Gmail-read to Pipedream and does NOT add `gmail.readonly`. Gmail-read stays on the existing provider (Unipile, `lm_users.gmail_provider`) and is OUT OF SCOPE here; for Telegram-first users the location-reply READ arrives via Telegram (`telegram-reply.js`), not Gmail. (The earlier "reply-by-email, never read Gmail" claim was FALSE and is removed.)
- **MIGRATION (F4, corrected per FIND-003)**: BOTH selector sites hardcode `calendar_provider=eq.composio_gcal` — `scheduler.js:42` (batch scan) AND `getUserByUid` `scheduler.js:271` (Inngest per-user refetch behind wakeUserOnce/travelUserOnce/askUserOnce). BOTH must widen to `in.(composio_gcal,pipedream_gcal)`, else a Pipedream user is picked in the batch but re-excluded on refetch. Dual-read until Composio users migrate.
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
- **MONITOR HOST (OQ4 resolved)**: the 15-min money-path monitor runs as a **GitHub Actions scheduled workflow** (independent of Railway/Netlify) so the monitor never dies with the monitored system (self-heal principle).

### C7 — Self-improve loop (LM only) (F10)
- **IN** daily tick. **OUT** LM metrics snapshot + report; ≥1 action when a non-noise signal exists.
- **GRADER at $0 (F10)**: do NOT gate on MRR-delta (noise at N=3); fitness = LEADING indicators (funnel-step conversion, activation, cost-per-outcome). NO-OP is valid when even leading signal is absent (reconciles Goal 8 with rule-5). Portfolio version = separate epic.
- **INVARIANT**: every action verified by real side-effect; no X; human only on a single escalation channel.

## 4. Verification architecture (Phase 1b seed)
- **RED (node --test, real fixtures)**: C2 parse against `evidence/fixtures/transit-plan-*.json` + `guidance-*.json`; C2 JP-bounds/resolvability + mixed-endpoint fallback; C3 cache call-count + moved-event invalidation; C1 fallback ordering + "ws-not-opened on default" counter; C5 assertion logic (bundle string → detect wrong/right link) + debounce + flap-guard + telegram-dedup; C6 rollback trigger.
- **NO-MOCK E2E (mine, after adversary PASS)**: real wake call on cheap path (hear it + Live-counter=0); money-path monitor vs live prod; Pipedream test-connect (cal+gmail) + confirm scheduler selects the user; `gcloud` key-restriction query.

## 5. Open questions — RESOLVED in-spec (F7)
- **OQ1 (default TTS)**: RESOLVED — `edge-tts` (free MS cloud); JP+EN tested, μ-law 8k exact; pre-synthesize before dialing so TTS latency is off the call path; fallback edge-tts→Kokoro/piper→Live.
- **OQ2 (transit ToS/coverage/limits)**: RESOLVED — free, unofficial, no SLA; ToS REQUIRES consumer-side cache+retry+fallback+official-redirect and forbids excessive requests/posing-as-official → satisfied by C3 cache + C2 Google fallback + advisory framing. Coverage = 748 operators incl JR East (broad JP). Non-JP/rural → Google.
- **OQ3 (Pipedream Gmail scope vs CASA)**: RESOLVED (corrected) — Pipedream grants Calendar + `gmail.send` only (sensitive, not RESTRICTED → no CASA). Gmail-READ (ask/notify's `mail-gog gmail search`) is NOT migrated to Pipedream and is OUT OF SCOPE; it stays on the existing provider; Telegram-first users get location-reply reads via Telegram. No `gmail.readonly`, no CASA trap.
- **OQ4 (monitor host)**: RESOLVED — GitHub Actions scheduled workflow (independent of Railway/Netlify).
- **OQ5 (key restriction vs Live fallback)**: RESOLVED — dedicated LM key restricted to `generativelanguage.googleapis.com` (+ Railway IP); the Live fallback is also generativelanguage → restriction does not break it. Enumerate other consumers of the old key before rotating.
