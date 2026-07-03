# Life Manager — Cost / Connect / Reliability — Behavioral Spec (VCSDD, lean)

- **Feature**: `life-manager-cost-connect-reliability`
- **Date**: 2026-07-03
- **Author**: Claude Code (dev IDE, = VCSDD builder) with Dais
- **Status**: Phase 1a (behavioral spec) — awaiting adversary spec-review (`/vcsdd-spec-review`)
- **Mode**: lean · **Language**: typescript/node (apps/life-call) + Next.js (apps/landing)
- **Grounding = REAL data gathered live 2026-07-03 (not hypothetical)** — see §1.

---

## 0. REALITY CHECK (measured 2026-07-03, not self-reported)

- **Revenue**: $0. Stripe LM subscriptions = 0, `lm_stripe_events` = 0 rows, `lm_users` = 3 rows (all Dais's own tests). Verified via live Stripe API + Supabase REST.
- **The pay-link bug is already FIXED this session** (separate hotfix, not part of this spec): the live `/lm` Subscribe button pointed to `buy.stripe.com/00w9ATf8...` = ¥700,000 one-time "AI供養" (gravestone) instead of `9B600j6C...` = LM $20/mo. Fixed via GH secret update + GHA redeploy + browser-verified. This spec exists so that class of failure is caught automatically forever (§4).
- **Google bill (why "$100")** — measured in GCP billing console (project anicca-461216, billing acct 017949-09509F-6A3FB6) via daily-driver browser:
  - **Gemini API = the dominant driver**: ¥268 on 2026-07-01 alone (Project Anicca, Region global) → ~¥8k/mo run-rate. This = the voice model `gemini-2.5-flash-native-audio-preview-09-2025` (Gemini Live native-audio, premium per-token audio billing) called **2×/event (T-10, T-5)** + `gemini-2.5-flash` text for ask/notify.
  - **Google Maps Platform — Routes = secondary driver**: SKU `Routes: Compute Routes Pro` (premium `TRAFFIC_AWARE_OPTIMAL`), region asia-southeast1, recently swung −¥913. Called from `scheduler.js` scanning events on a 60s tick.
  - **Security flag (GCP banner)**: the Gemini API keys are **unrestricted** → unauthorized-usage/cost risk. MUST restrict.
  - With **one user (Dais)** this = ~$100/mo. Unsustainable at $0 revenue.

## 1. Verified external facts (sources)

| Fact | Source (live) |
|---|---|
| Voice model = `gemini-2.5-flash-native-audio-preview-09-2025`, voice Charon | `apps/life-call/lib/call-logic.js` (read) |
| Wake calls = T-10 + T-5 (2/event) | `apps/life-call/scheduler.js` `WAKE_LEVELS` (read) |
| Maps = Routes API `computeRoutes` TRAFFIC_AWARE_OPTIMAL + legacy Directions transit | `apps/life-call/lib/travel.js` (read) |
| Gemini API ¥268/day, Routes Pro −¥913 | GCP billing report, browser screenshot 2026-07-03 |
| **Free JP transit API** `https://api.transit.ls8h.com` — auth-free, CORS-open, read-only, OpenAPI | live-tested: `GET /api/v1/plan?from=geo:35.681,139.767&to=geo:35.690,139.700` → 4 journeys, 中央線快速, durationSecs, transfers, walk secs. `GET /api/v1/guidance/plan` = ranked options + map geometry. `/api/v1/places/suggest` + `/places/reverse` = JP geocode/autocomplete |
| **Free TTS options** (voice cost cut) | GitHub live: `rany2/edge-tts` (MS Edge TTS, no API key, free), `hexgrad/Kokoro` (OSS SOTA-tiny), `rhasspy/piper`, `k2-fsa/sherpa-onnx` |
| **Pipedream Connect** = one managed OAuth for BOTH Gmail + Calendar | `pd` CLI installed (v0.6.1); keys in `~/.openclaw/.env` (PIPEDREAM_CLIENT_ID/SECRET). Solves the Composio-Calendar-vs-Gmail split |
| show-me-the-money skill present | `~/.claude/plugins/cache/show-me-the-money/money/1.0.0/` |

## 2. Goal (provable finish line — GLVS)

`done` = **Life Manager's per-user monthly Google cost drops from ~$100 to <$10 with NO quality regression on the wake call, the Gmail+Calendar connect works through ONE OAuth, and a machine (not Dais) continuously verifies the money-path + heals it — all proven by real side-effect E2E, adversary PASS, and my own browser/call verification.**

Verifiable conditions (each MUST be demonstrated with fresh evidence):
1. **VOICE-COST**: a real wake call is placed end-to-end using the new cheap path (cheap-text line + free TTS + Telnyx), Dais hears it, and the call incurs **$0 Gemini-Live** cost (billing shows no native-audio token spend for that call).
2. **ROUTE-JP**: for a JP origin/destination, travel time + guidance come from `api.transit.ls8h.com` (verified against a known route), and Google Routes Pro calls for that path = 0.
3. **MAPS-CACHE**: the 60s scheduler no longer recomputes a route it already has; a route is computed at most once per (uid, event, coarse-time-bucket) — proven by a call-count assertion.
4. **CONNECT**: a test user connects Google Calendar AND Gmail through Pipedream Connect via ONE consent, and the backend can read calendar + send/read mail for that user.
5. **MONEY-PATH MONITOR**: an external synthetic check asserts (a) site 200 on `/ /life-manager /lm /lm?tg=`, (b) the live `/lm` bundle's Stripe link == the known-good LM $20/mo link, (c) the Stripe page shows "Life Manager" + "$20". On mismatch it auto-rolls-back to the last-good Netlify deploy and sends Dais exactly ONE Telegram.
6. **DEPLOY-SAFETY**: the GHA `netlify-deploy.yml` runs a post-deploy smoke (conditions 5a/5b) and auto-restores the previous deploy on failure — proven by injecting a bad build in a preview and observing rollback.
7. **KEY-RESTRICT**: the Gemini API keys are restricted (referrer/IP/API scope) so the GCP "unrestricted key" banner clears.
8. **SELF-IMPROVE LOOP**: a daily `/loop` (Sonnet) reads real metrics (Stripe MRR, Supabase signups, funnel conversion, Google spend, money-path result) and takes ≥1 concrete action, persisting a report (show-me-the-money `/money-save`→`/money-report`). Proven by 1 real cycle producing a committed report + a real action (e.g. a post to a non-X platform, a copy A/B, a cost fix).

## 2.1 Non-goals (out of scope here)

- Distribution content strategy specifics (PH copy, which platforms) — a separate feature.
- The self-funded (`skills/earn/ai/`) crypto pipeline — colony spec owns it.
- No X posting (Dais constraint). Other platforms allowed.

## 3. Behavioral contracts (in → out / edge / error / invariant)

### C1 — Voice (cheap path)
- **IN**: a due wake (uid, event, urgency ∈ {firm, harsh}, resolved route/leave-time).
- **OUT**: a phone call whose audio is a spoken guidance line in the user's `call_language`, produced by cheap-text-gen + free TTS, played over the existing Telnyx bridge.
- **EDGE**: TTS provider down → fallback provider (edge-tts → Kokoro/piper local) → last resort Gemini Live (billed, logged as fallback). A call MUST NOT be silently dropped.
- **ERROR**: no audio produced → do NOT dial (a silent call is worse than none); log + count.
- **INVARIANT**: default path emits **zero** Gemini-Live audio tokens. Native-audio only on explicit fallback.
- **QUALITY BAR**: the line still names event + place + route + urgency (same content as today), in the right language.

### C2 — Routing (JP via transit.ls8h.com, non-JP via Google)
- **IN**: origin geo + destination geo/place + depart/arrive time.
- **OUT**: `{ durationSecs, legs[], guidance }`. JP (both endpoints resolvable in the feed) → `api.transit.ls8h.com`; else → existing Google path.
- **EDGE**: transit API returns 0 journeys (e.g. Routes-only rural) → fall back to Google for that request.
- **ERROR**: transit API non-200/timeout → fall back to Google, log.
- **INVARIANT**: no secret/API key sent to transit API (it is auth-free); PII (home address) resolved to geo before the call where possible.
- The MODEL (agent), not a regex, decides JP-vs-not and online-vs-physical (HARD: build-agents-not-hardcode). Deterministic code only parses the API response + does arithmetic (leave = start − duration − buffer).

### C3 — Maps cache
- **IN**: a route request (uid, from, to, time-bucket).
- **OUT**: cached result if present in `lm_travel_log` within TTL; else compute once + store.
- **INVARIANT**: for a given (uid, event, coarse-time-bucket), external route providers are called ≤1×. TTL + bucket defined so a moved event still recomputes.

### C4 — Connect (Pipedream) — ONE consent for Calendar + Gmail; TELEGRAM-ONLY onboarding
- **DECISION (Dais 2026-07-03)**: **Telegram (@LifeManagerBotbot) is the SOLE onboarding for the foreseeable future** — no app download, no site to navigate; if you have Telegram you're in. The web `/lm` onboarding stays built but gated; do not center it.
- **DECISION**: Pipedream Connect issues **ONE OAuth consent that grants BOTH Google Calendar AND Gmail** → we RE-ADD the Gmail step that was removed from Telegram onboarding, and it costs **one fewer** onboarding step overall (cal+gmail collapse into a single tap), not one more.
- **IN**: user taps a single Connect link from the Telegram bot → one Pipedream Connect consent.
- **OUT**: backend holds ONE connected-account id able to (a) read/write Calendar, (b) send + read Gmail for that user.
- **EDGE**: partial grant (calendar but not gmail) → onboarding reflects true state; do not claim gmail if absent.
- **INVARIANT**: no Google RESTRICTED-scope audit trap re-introduced without a decision (see OQ3); secrets never logged.
- **MIGRATION**: existing Composio-calendar users keep working (dual-read) until migrated.
- **TELEGRAM FLOW (target)**: `/start` → name (chat) → phone (chat) → **ONE tap: Connect Google (Calendar+Gmail via Pipedream)** → **ONE tap: Subscribe $20/mo** → done. Only the two OAuth/Stripe taps leave chat; everything else is native Telegram.

### C5 — Money-path monitor + C6 deploy smoke/rollback
- **IN**: a schedule (≤15 min) + each production deploy.
- **OUT**: PASS/FAIL per assertion; on FAIL → auto-rollback (`deploys/<last-good>/restore`) + ONE Telegram.
- **INVARIANT (SRE)**: black-box + **content assertion** (200 is not enough — assert the actual Stripe link value + product/price text). Low-noise: page a human only on a real, ongoing symptom (Google SRE golden-signals / symptom-vs-cause).
- **KNOWLEDGE**: known-good values (Stripe link, deploy id) live in a small registry file, not hardcoded across the codebase (SSOT, HARD 0.17).

### C7 — Self-improve loop (LM) → extends to C7-EXT Portfolio loop
- **IN**: daily tick.
- **OUT**: a metrics snapshot + ≥1 action + a persisted `/money-report`, committed & pushed.
- **INVARIANT**: every claimed action is verified by real side-effect (GLVS); no X posting; human is not in the loop except a single escalation channel.

### C7-EXT — PORTFOLIO self-improvement loop (grounded in 2 deep-research passes 2026-07-03)
Applies the SAME loop to every product in `aniccaai.com/dais` + `anicca-project`, not just LM.

**Loop shape (universal, from Warp/Reflexion/Self-Refine/Anthropic evaluator-optimizer)** — two nested loops; improvement is stored as TEXT in a versioned `SKILL.md` (Reflexion: verbal memory, not weights), the repo is the STATE (GLVS):
- INNER (per task): apply a product/marketing skill → real side-effect → record a trace stamped `skill:<name> v:<N> run_id:<...>`.
- OUTER (daily `claude -p` Sonnet): observe traces+git since last bump → GRADE by metric delta attributed to the version window → synthesize ≤ a few GENERALIZABLE lessons → diff the skill + bump version → open a PR (never push main).

**7 hard rules (load-bearing, or the loop degrades)**: (1) grounded external signal, not self-opinion — here the grader = **metric delta (MRR/signup/conversion/cost)**; (2) generalizable-only lessons; (3) bounded guidelines (≤~12, consolidate/prune at cap); (4) versioned skill + trace marker for attribution; (5) weak/conflicting signal = NO-OP (empty run is success); (6) weighted evidence (MRR-drop/relabel=strong > engagement=moderate > silence=weak-positive); (7) PR gate + audit trail — no-human review is replaced by **fresh-context vcsdd-adversary on the diff + a regression guard (if the previous bump's metric got WORSE, REVERT it, don't stack)**.

**show-me-the-money = ADAPT, not use-as-is** (`~/.claude/plugins/cache/show-me-the-money/money/1.0.0/`, CC BY-NC OK): it's NL prompts with PLACEHOLDER metrics + human-in-loop gates + an X-posting arm. REUSE = `money-ops` 6-dim health-score bottleneck-picker, `~/.smtm/` state spine (`/money-save`,`/money-learn`,`/money-retro`,`/money-report`), `money-finance` business-type→metric router. REPLACE = wire real metric reads (deterministic tools write today's numbers to `~/.smtm/analytics/<slug>.jsonl` BEFORE the agent reasons — agent judges, tools fetch); swap human confirmation for adversary + browser E2E; AMPUTATE `money-social` X path.

**Funnel-lever priority at $0 MRR (AARRR, but NOT acronym order)**: 0 Instrumentation → 1 **Activation** (fix the leaky bucket before scaling traffic) → 2 Retention (churn caps MRR; target <5%/mo, NRR>100%) → 3 Revenue/Paywall (trial→paid>10%; reprice when conv<5%=too dear or churn<2%+high-use=too cheap) → 4 Acquisition (compounding organic) → 5 Referral. Pick the lowest BROKEN UPSTREAM stage, one product × one lever × one action per day.

**Marketing WITHOUT X (Dais bans X)**, effectiveness order: programmatic SEO + GEO (AI-citation: schema/JSON-LD → cited by ChatGPT/Perplexity/Gemini) + directory submissions > paid ads > cold email (warmed domain, bounce<5%) > Product Hunt (episodic). Drop X entirely.

**Metrics per product + source**: MRR/churn/subs/failed-pay → Stripe API/CLI; mobile subs/trial→paid → RevenueCat MCP (`get-overview-metrics`,`get-revenue-metric`); downloads/ASC conversion/proceeds(3-day lag, weekly-smooth) → `asc` CLI; signups/activation/D7-D30 → Supabase SQL; traffic/LP-conv → GA4. Derived: growth MoM, ARPU, CAC, **LTV:CAC>3**, payback<6mo.

**Daily loop (no human, no X)**: [1] PULL metrics (deterministic) → [2] SCORE+PICK one product×one bottleneck → [3] SPEC the one action (VCSDD, right-altitude, agent decides — no hardcoded branch) → [4] BUILD (SDD RED→GREEN, commit+push) → [5] VERIFY (① adversary disk-only ② my browser/on-chain E2E: curl 200 + Supabase event fires + Stripe/RC reflects; NO mock) → [6] PERSIST (money-save/learn + report row before→after+evidence+next bottleneck) → [7] GUARDRAILS (spend cap, new channel 10%→scale over 6d, canary 24h auto-flag on −50%×2, panic-stop) → next product; weekly money-retro rolls up portfolio.

**Anti-patterns (Project Vend — Claude ran a real shop 1mo and LOST money)**: selling at a loss / talked into discounts / missing lucrative offers / hallucinating payment details / not learning across runs / vanity metrics / unverified "done". Guards: LTV:CAC>3 enforced, no autonomous discounting, score-driven action, HONESTY+real-read, STATE memory, load-bearing-metric-only, E2E-mandatory.

**Ownership**: human-funded instance (this Claude, on a Claude sub) may run `earn/human/` + `earn/ai/`; self-funded instances run `earn/ai/` only (no human credentials). This C7-EXT loop = the `earn/human/` product-operator engine.

**Sources (verified 2026-07-03)**: Warp issue-triage-loop (inner/outer + 7 rules); Reflexion arXiv 2303.11366; Self-Refine 2303.17651; Anthropic Building-Effective-Agents + Effective-Context-Engineering; MT-Bench LLM-as-judge 2306.05685; Hamel "Your AI Product Needs Evals"; AARRR (McClure/500 Startups); programmaticseo.com + ahrefs GEO; Anthropic Project Vend; show-me-the-money v2.5.1 skill source.

## 4. Architecture delta (ASCII)

```
  BEFORE (costly, fragile)                     AFTER (cheap, self-verifying)
  ─────────────────────────                    ─────────────────────────────
  wake → Gemini Live native-audio ($$$)        wake → cheap-text line → edge-tts/Kokoro ($0) → Telnyx
  travel → Routes Pro TRAFFIC_AWARE_OPTIMAL     travel(JP) → api.transit.ls8h.com (free) ; else Google
           every 60s, uncached                  cached in lm_travel_log (≤1 call / event / bucket)
  connect → Composio(cal) + Gmail blocked       connect → Pipedream Connect (cal + gmail, one OAuth)
  monitor → Dais's eyeballs                     monitor → money-path synthetic (15m) + GHA smoke → auto-rollback
  improve → manual, sporadic                    improve → daily /loop (show-me-the-money) metrics→action→report
```

## 5. Verification architecture (Phase 1b seed — to expand)

- **RED tests (node --test, no-mock where possible)**: C2 transit-parse (real fixture from live call), C3 cache call-count, C5 assertion logic (given a bundle string → detect wrong link), C6 rollback trigger, C1 fallback ordering.
- **NO-MOCK E2E (my job, after adversary PASS)**: place ONE real wake call on the cheap path (hear it); run the money-path monitor against live prod; connect a test Google acct via Pipedream.
- **Adversary (fresh context, disk-only)**: `/vcsdd-spec-review` now → then Phase-3 impl review. Binary PASS/FAIL per 5 dims.

## 6. Open questions (resolve in-spec before impl)

- OQ1: **RESOLVED (tested live 2026-07-03)** — default = **`edge-tts`** (Microsoft cloud TTS, free, no API key). Generated real JP (ja-JP-NanamiNeural 9.8s / ja-JP-KeitaNeural) + EN (en-US-GuyNeural 8.5s / en-US-AriaNeural) wake-call lines, valid mp3, played aloud on the Mac, and transcoded to G.711 μ-law 8kHz mono = **78,528 bytes = 9.816s × 8000 exact** → drops straight into the existing Telnyx bridge. Fallback chain: edge-tts → local Kokoro/piper (offline, if MS endpoint down) → Gemini Live (billed, last resort). Remaining sub-question = live PSTN latency budget (pre-synthesize the line before dialing → play as media, so TTS latency is off the call path).
- OQ2: transit.ls8h.com coverage + rate limits + ToS for commercial use (read `/利用規約`); SLA/fallback threshold.
- OQ3: Pipedream Connect Gmail scope = still Google-sensitive; does it avoid the CASA-audit trap Composio hit? (verify before migrating).
- OQ4: money-path monitor host — GHA cron vs an OpenClaw cron vs the life-call scheduler (pick per self-heal spec's "monitor must not die with the monitored").
- OQ5: does restricting the Gemini key break the Live fallback / other consumers? (enumerate consumers first).
```
