# Anicca / Life Manager — SINGLE AGENT SUBSTRATE (design) — 2026-06-24

superpowers:brainstorming output. Decision: pick ONE multi-agent harness so local / cloud / Capafy
run the SAME agent code, differing ONLY by who holds the keys. Everything is an AGENT + tools (no
judgment scripts). Cloud-hosted (no local disk pressure). Multi-agent by design.

## Vision (Dais 2026-06-24, verbatim intent)
- Local (OSS, BYOK) / Cloud (managed, $20/mo) / Capafy = SAME setup; only diff = key-holder.
- Self-improving: the agent changes WHEN to call + WHAT to say per user (memory of their likes/history).
- Omni-channel onboarding: Telegram now → LINE / WhatsApp / Discord / iMessage / more.
- Proactive: books good-for-you events (dentist, meetups) per your liking + its memory of you.
- Earn loop: own USDC wallet → earns to buy its own compute (→ eventually NO monthly subscription).
  Given a user's creds (bank/number/Stripe), earns FOR the user, all money to the user. End state =
  no creds needed (regulation lifts) → earns with zero human creds → merge with Anicca, drop
  /life-manager. Anicca = leads a human to their ideal self (financial / physical / mental), no human
  in the loop except the kickstart.
- Targets: 10k MRR total = 5k stars (OSS) + 5k/mo (web) + 5k/mo (Capafy).

## Harness comparison (4 parallel research agents, 2026-06-24, Firecrawl+ctx7+gh)
| dim | OpenClaw | Hermes (Nous) | Claude Agent SDK | claude -p + sutando |
|---|---|---|---|---|
| FIT | **8** | **8** | 7 | 7 |
| multi-agent | native 2-layer (routing + sessions_spawn, nesting) | native + self-learning loop | native subagents/teams | native subagents/teams |
| model-agnostic | ★~60 providers, config-only | ★any model (`hermes model`) | ✗ Claude-only (proxy hack) | ✗ Claude-only (role-split) |
| cloud host | Railway 1-click + ClawHost | Railway/Modal/Daytona | Railway/Docker self-host | SDK prims (sutando=mac-only) |
| BYOK↔managed | config only | BYOK + Nous Portal | same code, swap key | ToS: sub local / metered API cloud |
| voice PSTN | custom plugin (Gemini realtime supported) | weak (turn-based) | outside SDK | ★working Twilio+Gemini Live blueprint |
| multi-tenant | self-build (ClawHost=1 VPS/user) | weak (instance/user) | docs'd, you own | none |
| earn/wallet | none | none | none | none |
| our status | LOCAL runtime today | UPSTREAM of ~/.hermes | — | reference impl of the vision |

Sources: github.com/openclaw/openclaw + docs.openclaw.ai + railway self-host + antoinersx/clawhost;
github.com/NousResearch/hermes-agent; code.claude.com/docs agent-sdk + platform.claude.com managed-agents
+ musistudio/claude-code-router; github.com/sonichi/sutando. (Star counts reported by agents looked
inflated — NOT independently re-verified; qualitative findings are consistent and cited.)

## Three insights
1. OpenClaw & Hermes are the SAME lineage = what we already run → least migration, keep skills.
2. The 3 gaps (PSTN voice, multi-tenant SaaS, earn/wallet) are COMMON to ALL candidates → the decision
   is "best base + build the 3 gaps as agents/plugins," not "which fills them."
3. Claude SDK / claude -p are model-locked to Claude (violates our model-agnostic META-RULE) and ToS
   forbids reselling a subscription across hosted tenants (→ metered API → thin margin at $20/mo).

## CORRECTION (Dais 2026-06-24): HARNESS-PORTABLE, never vendor-locked
The product is NOT "OpenClaw as THE harness." The product = a HARNESS-PORTABLE package that makes ANY AI
(on OpenClaw, Hermes, Claude Code, or future harnesses) manage a human's life + earn money, no human in
the loop. Support any harness, any model. We START on OpenClaw — that is all. The package =
(1) harness-neutral AGENT definitions (orchestrator + call/calendar-travel/ask-notify/earn/omni),
(2) TOOLS as MCP (harness-neutral), (3) SKILLS (agentskills.io standard), (4) deterministic WORKFLOW
modules (voice-bridge Telnyx⇄Gemini-Live, arithmetic, dedup). Capafy = the SAME package shipped as a
skill. Local/Cloud/Capafy differ ONLY by adapter + key-holder.

## WORKFLOW vs AGENT (right altitude — NOT everything is agentic)
Per building-effective-ai-agents.md ("Deterministic code only for tools+arithmetic+bookkeeping; judgment
→ agent; regex OK only for parsing fixed machine formats") + building-voice-agents.md ("Build an agent
only when complex judgment / hard rulesets / unstructured data; else deterministic suffices"):
- WORKFLOW (keep deterministic): voice transport (bidi rtp, μ-law transcode, setupComplete handshake,
  base64, VAD, greet-first); arithmetic (head-out = start−travel−buffer; T−15/10/5); bookkeeping/dedup
  (don't double-ask, dedup [Travel], posted.jsonl); fixed parsing (E.164, URL scheme, gcal fields);
  scheduler tick cadence; the tools themselves; the Telegram onboarding stage machine (predictable path).
- AGENT (LLM judgment, no regex): location classification (online/physical/ask, which address, landmark
  →web-search); when to call / what to say / tone (self-improving per user memory); which events to
  proactively book; ask wording + matching a reply to an event; late-notice judgment; earn strategy.

## DECISION (recommended)
**Start the package on OpenClaw (Hermes lineage we already run) — but design it HARNESS-PORTABLE so it
also runs on Hermes / Claude Code / any harness, any model. Build the 3 gaps as agents/plugins on top.**
Why: ~0 migration; model-agnostic (META-RULE satisfied); native multi-agent (orchestrator + subagents
= "everything is an agent"); omni-channel native (free onboarding expansion); cloud host solved
(Railway + ClawHost, idle-hibernate = cheap, no local disk); BYOK↔managed = config only = "same setup,
keys differ" exactly.

Gaps built as agents:
- VOICE agent = port existing apps/life-call Telnyx↔Gemini-Live bridge into an OpenClaw gateway-relay
  plugin (we already have a WORKING bridge; sutando's Twilio+Gemini-Live server = blueprint, Twilio→Telnyx).
- EARN agent = existing x402/Base-MCP/wallet as a skill (self-fund compute; earn-for-user given creds).
- MULTI-TENANT = ClawHost's proven pattern: 1 paying user = 1 isolated instance (Daytona/Modal hibernate)
  + thin tenant-router + Stripe. NOT a shared gateway (unproven/risky).

Borrow from sutando: Core-agent + tasks/→results/ file bridge + cron `/proactive-loop` + Monitor tool
for the self-improvement loop.

## BP CORRECTION (re-read building-effective + voice md, 2026-06-24): SINGLE-AGENT FIRST
voice md: "Single-agent first; split only when branches don't scale or >~15 overlapping tools confuse the
model." agents md: "add multi-step agentic systems only when simpler solutions fall short." → Do NOT
pre-split into 5 sub-agents. CORE = ONE augmented Life-Manager agent (LLM + tools in a loop, per-user
memory). calendar/travel/ask/notify are TOOLS that one agent calls — NOT separate agents. Split into a
specialized sub-agent ONLY where BP justifies: (1) VOICE realtime loop (latency-critical, separate
Telnyx⇄Gemini-Live process), (2) EARN loop (separate long-running money process). So "multi-agent" =
a FEW coarse agents (life-orchestrator + voice + earn), grown as scale demands — not one-agent-per-feature.
Guardrail (voice md L81-82): gate irreversible spend/book (proactive booking, earn payout) behind a check.

## BUILD ORDER (Dais 2026-06-24): OpenClaw FIRST, then other harnesses — not all at once
Phase 2 builds the portable package on OpenClaw and gets it fully working there FIRST. ONLY after it runs
end-to-end on OpenClaw do we add adapters for other harnesses (Hermes, Claude Code, …). Harness-portable
is the DESIGN GOAL (keep the package harness-neutral: agent defs + MCP tools + skills + workflow modules),
but the ROLLOUT is incremental: OpenClaw → prove → then port. We start from OpenClaw, that is all.

## Agent topology (target)
```
ORCHESTRATOR agent (self-improving: per-user memory → when to call / what to say / what to book)
 ├─ CALL agent        — Telnyx ⇄ Gemini Live (Charon), tools: place_call, telnyx, gemini-live
 ├─ CALENDAR/TRAVEL   — tools: Google Routes API, calendar (Composio|gog), web-search-address
 ├─ ASK/NOTIFY        — tools: messaging channels, classify-late, write-calendar
 ├─ EARN/MONEY        — tools: USDC wallet, x402, Base-MCP, (user creds when granted)
 └─ OMNI-CHANNEL      — tools: Telegram/LINE/WhatsApp/Discord/iMessage Bot APIs
3 deployments (LOCAL BYOK / CLOUD managed / CAPAFY) = SAME agents; diff = adapter + key-holder.
```

## OpenClaw PORT PLAN — concrete, low-cost (researched 2026-06-24, ctx7+firecrawl + live ~/.openclaw)
KEY: the code is ALREADY ~80% portable. `lib/transport/index.js` switches `LIFE_TRANSPORT=composio|gog`
= the BYOK(local)/managed(cloud) split ALREADY EXISTS. Do NOT rewrite geometry or voice — WRAP them.

Each piece → OpenClaw home (reuse vs rewrite):
| current | OpenClaw home | reuse? | effort |
|---|---|---|---|
| scheduler 60s wake tick | cron COMMAND `*/1` → `node scripts/tick.mjs` (require existing exports) | reuse logic, ~30-line entry | S |
| travel loop 30m | cron COMMAND `*/30` → fillTravel (already exported) | reuse | XS |
| ask loop 20m | cron COMMAND `*/20` → askTickAll | reuse | XS |
| lib/travel.js (geometry+gcal) | called by travel cron entry, unchanged | reuse 100% | none |
| lib/ask.js (Gemini+places agent loop) | called by ask cron entry, unchanged | reuse 100% | none |
| server.js voice /ws (Telnyx⇄Gemini Live) | launchd/systemd KeepAlive daemon (NOT cron — always-on; precedent: ai.anicca.pipecat-phone) minus the start*Loop() calls | reuse, split loops out | S |
| lib/transport/* (composio|gog) | unchanged — LIFE_TRANSPORT env = the cloud/local switch | reuse 100% | none |
| Telegram bot + /telegram webhook | OpenClaw native telegram channel + agent; reuse reply/onboard FUNCTIONS, drop webhook plumbing | reuse fns | M |
| Supabase / Stripe | unchanged (env keys) | reuse | none |

DECISION: **cron-COMMAND wins for the 3 loops** (deterministic node on the gateway host, ZERO model spend
= 1:1 with today's setInterval). MCP-wrap is MORE work — reserve it ONLY for tools the chat agent calls
mid-conversation (e.g. "resolve this location now" on a Telegram reply). For scheduled work, cron-COMMAND.
BYOK vs managed = config only: transport env + `agents.defaults.model` / per-agent auth profile. Voice stays
pinned to Gemini Live (Charon) regardless (a Telnyx/Gemini key, not the agent's chat model).

HOSTING: paid privacy → 1 instance per tenant (ClawHost dedicated VPS, or Railway-per-tenant); voice bridge
rides as a KeepAlive daemon on the same host (cloud → zero local-disk pressure). OpenClaw native multi-agent
(shared gateway, agents.list[]) is cheapest but softer isolation ("true isolation = one agent per person").
CAPAFY = the SAME skill dir via capafy-publisher (run_online + subscription); only listing metadata differs.

ORDER (keep apps/life-call LIVE while porting — zero downtime):
1. keep Railway running. 2. build skills/life-manager/ (SKILL.md + scripts/{tick,travel,ask}.mjs = ~30-line
require()s, no lib changes). 3. register 3 cron COMMAND jobs (via `openclaw cron create`, NOT hand-edit
jobs.json — cron now in SQLite; doctor --fix reverts manual edits) against a tenant filter so no double-dial.
4. voice daemon as launchd KeepAlive (server.js minus loops) → verify one /test-call. 5. cut ONE pilot user
to OpenClaw, verify wake+travel+ask+voice E2E. 6. flip remaining users, disable Railway scheduler (keep
Railway voice as fallback one release). 7. wrap for Capafy from the same skill dir; add MCP later only for
on-demand chat tools. Honest: OpenClaw has no native always-on web service (voice = daemon); Railway template
is community (arjunkomath/openclaw-railway-template); ctx7 hit quota → OpenClaw claims cross-checked vs live
~/.openclaw/openclaw.json.

SEQUENCING vs edge-cases: the edge-case fixes (memory tools + REQ-15) live in lib/ask.js + lib/travel.js —
the EXACT libs the port reuses 100%. So FIX EDGE CASES FIRST (Phase 0), then port (Phase 2 V1) so the port
inherits a working LM and we don't port a half-working product.

## Migration path (don't break the launch)
- Phase 0 (now): apps/life-call (cloud) keeps running — it earns; launch proceeds.
- Phase 1: define OpenClaw agent topology (orchestrator + 5 subagents via agents.list[] + sessions_spawn);
  move planner/travel/ask/notify from Node scripts to agent prompt+tools (judgment→agent, deterministic→tools).
- Phase 2: wrap Telnyx↔Gemini-Live as a voice plugin/node.
- Phase 3: 1-instance-per-tenant on ClawHost/Railway + tenant-router + Stripe.
- Phase 4: earn agent (wallet/x402) = self-fund.
- Phase 5: merge with Anicca → drop /life-manager; one repo, one Anicca.

## Status / sequencing
This is the END-STATE substrate. It does NOT block the current launch (LAUNCH-ORDER A→E). Start Phase 1
AFTER the Capafy/PH launch milestones (or in parallel as a separate worktree) so we don't destabilize the
earning cloud app. NOT merging with Anicca yet — in coming weeks, once earn is proven standalone.
```
