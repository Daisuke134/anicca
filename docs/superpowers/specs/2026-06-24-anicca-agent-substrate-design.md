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

## DECISION (recommended)
**Substrate = OpenClaw (Hermes lineage we already run). Build the 3 gaps as agents/plugins on top.**
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
