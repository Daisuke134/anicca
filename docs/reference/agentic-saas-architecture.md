# Agentic Multi-Tenant SaaS — Architecture Reference (researched 2026-06-24)

THE canonical "how to build + sell an AI agent as a subscription SaaS to everybody, no human in the loop"
doc. Researched across 4 parallel agents (web + docs + GitHub + the live codebase). Read this BEFORE any
architecture debate so we never re-research. Pairs with `~/.claude/rules/building-effective-ai-agents.md`.

## 0. TL;DR decision (what we build)
**Bespoke POOLED multi-tenant app (one shared cluster, every user = a row keyed by user_id) whose JUDGMENT
steps are an agent loop (`@openai/agents`, already a dep) over our tools, with a DURABLE scheduler (Inngest)
replacing setInterval, memory in mem0ai/Postgres, Stripe webhooks as the billing source of truth, and a
hand-rolled Telnyx↔Gemini-Live voice bridge.** NOT per-user OpenClaw/ClawHost instances. NOT the Claude
Agent SDK. NOT a heavy framework. This is exactly what every scaled agent-SaaS does (see §3).

## 1. Multi-tenancy: POOLED, not per-customer instance (decisive, documented)
When you sell an agent as subscription SaaS to many customers you run ONE shared multi-tenant app keyed by
`tenant_id`/`workspace_id`/`user_id`, per-tenant config + OAuth tokens + memory, and a STATELESS shared LLM
call per request. The model is stateless; tenancy is a DATA/CONFIG-layer decision, not a model/instance one.
- AWS: pooled = "the classic notion of multi-tenancy… economies of scale… essential to the SaaS model";
  "instance per customer running separate versions" = "a managed service model… differentiated from SaaS."
  (docs.aws.amazon.com/wellarchitected/latest/saas-lens/silo-pool-and-bridge-models.html ; aws.amazon.com/
  blogs/machine-learning/build-a-multi-tenant-generative-ai-environment-for-your-enterprise-on-aws/)
- Real products → ALL pooled (none ship "your own VM" by default):
  - **Viktor** (Slack/Teams AI employee, 40k+ teams): "walled off per workspace, no cross-tenant access,
    one-click install, NO infra to provision" (viktor.com/security).
  - Slack platform: one app (client_id) → any workspace installs via OAuth → per-install xoxb token keyed by
    team.id → ALL workspaces' events hit ONE request URL carrying team_id (docs.slack.dev).
  - Decagon "most customers run multi-tenant" + per-tenant throttling; Intercom Fin = one Rails monolith →
    shared Aurora ("have not come close to needing" a dedicated shard); Ada per-tenant namespaces; Cresta
    per-customer orgs on shared K8s; Gumloop shared static egress IPs; Zapier shared worker fleet; Devin =
    pooled stateless brain + ephemeral per-session sandbox; Lindy/Dust pooled.
- SILO (dedicated instance/VPC) = premium enterprise/compliance carve-out only (Sierra VPC, Devin Dedicated),
  deliberately under-advertised, never the $20/mo default. AWS: silo "undermines economies of scale."
- → PER-USER OpenClaw/ClawHost instances = personal-hosting/managed-service artifact, NOT scaled SaaS.

## 2. Substrate: bespoke app + agent loop. Framework/gateway NOT required.
Anthropic: agent = "LLMs dynamically direct their own processes and tool usage… typically just LLMs using
tools based on environmental feedback in a loop"; "the most successful implementations weren't using complex
frameworks… start by using LLM APIs directly" (anthropic.com/engineering/building-effective-agents). So a
normal multi-tenant app whose decision points are LLM-tool-loop calls ALREADY IS an agent — no gateway.
- OpenClaw/Hermes = personal/dev tools; their own docs say OpenClaw is "NOT a hostile multi-tenant security
  boundary" → wrong for a product. No production agent-SaaS runs them as substrate.
- Claude Agent SDK = genuinely multi-tenant but heavy (1 GiB subprocess/session, per-token API) → only for
  agents needing a real per-tenant shell/filesystem/code-exec (coding agents). Overkill for calls+voice+cal.

## 3. What real agent-SaaS actually build on (framework vs bespoke)
- AI-native agent companies (OUR category) = BESPOKE in-house, on raw vendors. Documented:
  - **Viktor (viktor.com)** = bespoke Python harness on **Modal**, per-workspace Linux sandbox, code-writing
    agent, self-written skill files. NOT OpenClaw/Hermes/Claude-SDK/LangGraph — it's OpenClaw-*shaped*
    (code-mode) but from scratch, and markets itself as the managed alternative TO OpenClaw
    (viktor.com/compare/viktor-vs-openclaw, viktor.com/research/*). Dais's hunch ("Viktor ~ OpenClaw") =
    half-right: same pattern, NOT the same software.
  - Lindy founder Flo Crivello (on record): "we don't use any higher level solutions… in-house… I would do
    it again" (cognitiverevolution.ai Living-Lindy). Sierra = proprietary "Agent SDK" (not public). Decagon =
    "Agent Operating Procedures" compiled to code, bashes "rigid frameworks." Cognition "builds Devin with Devin."
- Enterprises BOLTING agents onto existing SaaS = OSS, **LangGraph** most-cited (Uber, Klarna, Elastic,
  Cisco, Coinbase, LinkedIn). (INFERRED split — no rigorous public survey.)
- → "Build bespoke" is NOT laziness; it's the deliberate choice of every scaled competitor, Viktor included.

## 4. The ONE real gap = durable per-user scheduling at scale → Inngest
"Call 15 min before each calendar event for 10k users" needs a CENTRAL SWEEPER + FAN-OUT, not per-user cron.
- Per-user cron (Vercel/Supabase) = DISQUALIFIED (Vercel caps 100 jobs/project, config-only).
- Pattern: one cron function runs every minute → queries all users' upcoming events → `step.sendEvent` fan-out
  one durable job per imminent call → per-user concurrency `key: user_id` for fairness (no noisy neighbor) →
  auto-retry + per-tenant error isolation.
- Framework ranking for OUR Node/Express/Prisma/Railway app (gh stars / license / fit):
  1. **Inngest** (inngest/inngest 5.5k SSPL→Apache; SDK+AgentKit Apache-2.0) — durable cron sweeper +
     fan-out + per-user concurrency + retries + replay + tracing, drops on as a LIBRARY (no runtime rewrite),
     model-agnostic. AgentKit (agent loop sugar) optional/young → use Inngest core as the spine + our existing
     `@openai/agents` loop. Cloud free→$75/mo Pro (per step-exec). ★ RECOMMENDED ★
  2. **Cloudflare Agents** (cloudflare/agents 5.2k MIT) — Durable-Object-PER-USER = per-user state + DO-alarm
     self-scheduling + SQLite, scale-to-zero (idle≈$0), the most ELEGANT per-user-scheduling-at-scale primitive.
     BUT = Workers runtime (≠ full Node) → a platform migration (Telnyx/Telegram/Google/Prisma SDKs must be
     Workers-compatible). Reconsider only if we move the runtime onto Workers.
  3. **Trigger.dev** (15.5k Apache) — best OSS durable scheduler, per-user-timezone cron, queues; but NO agent
     loop (BYO) + our irregular "before each event" timing → you build a sweeper anyway → converges to Inngest.
  - NOT for us: Mastra (scheduler weak at large N + duplicates our agent layer), Temporal/Restate (ops overkill,
    no scheduler-conveniences nor agent loop), LangGraph/CrewAI/Pydantic/Agno (Python = migration tax; Letta
    only as an optional memory sidecar). No "agent SaaS starter" repo worth forking (matches are 0–7★ solo).

### 4b. Inngest — VERIFIED HANDS-ON 2026-06-24 (downloaded + ran, not README)
Installed `inngest` + `express` in a scratch app, ran the Inngest dev server, and proved the EXACT pattern
we need: a `* * * * *` cron sweeper fired automatically → `step.sendEvent` fan-out 3 events → 3 per-user
`wake-user` jobs executed → and the per-user `concurrency: { key: "event.data.userId", limit: 1 }`
SERIALIZED the same user's two jobs (u1 Dentist @.224 then u1 Lunch @.369, ~145ms apart) while a different
user (u2 @.227) ran in parallel = no double-call per user / noisy-neighbor fairness. Durable `step.run` ran.
GOTCHAS found by actually running it (the docs/research were slightly stale):
- ★ The installed-version API is `createFunction({ id, triggers: [{ event }|{ cron }], concurrency }, handler)`
  — 2 args, TRIGGERS IN THE FIRST CONFIG OBJECT. The 3-arg form `createFunction({id}, {event}, handler)` in
  older docs CRASHES ("Triggers belong in the first argument"). Use the 2-arg form. ★
- The local dev server only SYNCS the app when the SDK runs in dev mode → set `INNGEST_DEV=1` (else the
  endpoint returns `internal_server_error` and `functions: []`). In prod you use INNGEST_SIGNING_KEY/EVENT_KEY.
Verdict: Inngest delivers the cron-sweeper + fan-out + per-user-concurrency claims as a library on our
Express/Node stack. inngest/inngest ⭐5522 (pushed daily). Alternatives confirmed: cloudflare/agents ⭐5163
(elegant DO-per-user but a Workers-runtime migration), trigger.dev ⭐15461 (great scheduler, no agent loop).
ADOPT Inngest.

## 5. Voice bridge (Telnyx + Gemini-Live)
HAND-ROLL the WS bridge in Node (~few hundred lines). Hard parts already documented in
`~/.claude/rules/building-voice-agents.md`: `stream_bidirectional_mode:"rtp"`, μ-law 24k↔8k resample,
iterate ALL Gemini parts, wait for setupComplete, barge-in `clear`. Multi-tenants trivially (one WS/call).
LiveKit Agents = wrong shape (SIP/WebRTC media server, not raw Telnyx WS). If we ever want a framework:
**Pipecat** (BSD-2, native Telnyx serializer = our exact protocol, accept a Python service). Managed escape
hatch: Telnyx Voice AI Assistant or Vapi ($0.05/min, BYO-LLM).

## 6. Billing (Stripe) — webhook is the source of truth
checkout.session.completed/active → provision tenant row + entitlement; past_due/unpaid → suspend (deactivate
schedule+voice); canceled → deprovision. Use Stripe Entitlements for the access flag, Smart Retries/dunning ON
(Stripe owns retry logic). Idempotent webhook handlers (Stripe re-delivers). NEVER trust the client redirect.

## 7. What we ALREADY have (verified 2026-06-24, package.json)
- `apps/api` deps: **`@openai/agents` 0.4.4 (agent loop), `@anthropic-ai/sdk`, `mem0ai` 2.1.38 (memory),
  `openai`, `zod`** — on Express + Prisma/Postgres (Railway) + Supabase. = the agent loop + memory already exist.
- `apps/life-call` deps: only `ws` (the Telnyx⇄Gemini-Live voice + scheduler service).
- Scheduler today = raw `setInterval` in `apps/life-call/scheduler.js` + `apps/api/src/server.js` (the gap §4).

## 7b. MAINTENANCE-COST minimization = ONE core lib + transport adapter (already built; OpenClaw NOT needed)
The reason we wanted OpenClaw/open-core = ONE codebase across cloud/local/capafy so we don't maintain 3
things. That goal is ALREADY achieved WITHOUT OpenClaw via the transport-adapter pattern (#74/#76, verified
in code 2026-06-24): every core module (apps/life-call/lib/{events,ask,travel,notify,telegram-reply}.js)
imports `getCalendar()/getMail()` from `lib/transport/index.js`, which switches `LIFE_TRANSPORT=gog|composio`.
- ★ ONE shared CORE (lib + @openai/agents loop + tools + transport adapter) — fix once, all forms inherit ★
- CLOUD = core + entrypoint (Inngest sweeper, pooled all lm_users) + LIFE_TRANSPORT=composio + our keys.
- LOCAL (OSS/BYOK) = SAME core + small single-user launcher + LIFE_TRANSPORT=gog + BYOK keys + local trigger.
- CAPAFY = SAME core's travel/plan FUNCTIONS, wrapped as a reduced stateless skill (no calls/cron/voice).
- Diff cloud↔local = CONFIG ONLY (transport, keys, single vs pooled). cloud≈local ~95% identical; capafy ~30%.
HONEST: dropping OpenClaw LOWERS maintenance — OpenClaw would have ADDED per-user gateways + operator.admin/
pairing ops (the friction we hit 2026-06-24). Inngest + @openai/agents are LIBRARIES of the one core, NOT a
3-way fork. The low-maintenance/one-codebase win we wanted from open-core is preserved by lib+adapter.

## 7c. MODEL = GEMINI, no OpenAI spend (Dais has no OpenAI budget — verified 2026-06-24)
The agent loop runs on GEMINI, $0 OpenAI. We ALREADY use Gemini (ask.js agentResolveLocation = Gemini 2.5
Flash + places_search tool loop; voice = Gemini Live native-audio Charon). Two ways to keep the agent loop
on Gemini: (a) GEMINI-NATIVE — build the loop on the Gemini SDK we already use (Anthropic BP: "use LLM APIs
directly"); RECOMMENDED. (b) @openai/agents pointed at Gemini's OpenAI-COMPATIBLE endpoint
(ai.google.dev/gemini-api/docs/openai — base_url=https://generativelanguage.googleapis.com/v1beta/openai/ +
the Gemini API key) → @openai/agents runs on Gemini with NO OpenAI key. So earlier "@openai/agents (a dep)"
does NOT imply OpenAI cost — it's optional and only viable if pointed at the Gemini-compat endpoint. HARD-2
(scheduling) adds NO model dependency at all; the agentic loop is a later task and stays on Gemini.
Build subagents run `mode: "bypassPermissions"` (no human-in-loop — no permission prompts).

## 8. RECOMMENDED STACK (cleanest path to scale + future features)
**Inngest (durable scheduler+fan-out spine) + `@openai/agents` (agent loop, already a dep; optional AgentKit)
+ mem0ai/Postgres (per-user memory) + Stripe webhooks (billing) + hand-rolled Node Telnyx↔Gemini-Live WS
bridge — all on the existing pooled multi-tenant Express/Prisma/Railway app.** Optionally study Viktor's
documented code-mode pattern (viktor.com/research) for the self-improving/agentic layer later.

## Sources (every claim is cited inline above)
AWS SaaS Lens + GenAI ML blog · anthropic.com/engineering/building-effective-agents · viktor.com/{security,
compare/viktor-vs-openclaw,research} · docs.slack.dev · decagon.ai · intercom.com/blog · ada.cx/labs ·
cresta.com/blog · docs.gumloop.com · CNCF KEDA@Zapier · docs.devin.ai · cognitiverevolution.ai (Lindy) ·
github.com/{inngest/inngest,inngest/agent-kit,cloudflare/agents,triggerdotdev/trigger.dev,mastra-ai/mastra} ·
agentkit.inngest.com · developers.cloudflare.com/agents · code.claude.com/docs/en/agent-sdk · docs.openclaw.ai/
gateway/security · github.com/antoinersx/clawhost (per-user VPS cloud-init).
</content>
