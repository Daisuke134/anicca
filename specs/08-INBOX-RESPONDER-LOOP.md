# 08 — Inbox Responder Loop (= the part NO OSS does end-to-end)

> ⚠️ **RUNTIME NOTE (current):** This spec (DRAFT 2026-06-03, also flagged ARCHIVED-WITHIN-A-DAY in the
> README) names a **Hermes Agent daemon** as the 24/7 runtime + FTS5 memory + skill registry. That
> runtime choice was **reversed** — the current body is the **Conway automaton** (ReAct loop +
> heartbeat daemon), runtime root `~/.anicca` (`skills/registry.json`). Read every "Hermes daemon /
> `~/.local/bin/hermes` / `~/.hermes/state.db` / Hermes scheduler / Hermes FTS5 memory" below as
> "**the automaton runtime** (loop + heartbeat + its memory/skill store)". The inbox-loop *design*
> (event ingest → context-aware reply → durable multi-step state → 24h followup → learn-from-outcome)
> stands; only the runtime label is stale. See `00-MASTER.md` / `16-RUNTIME-CODE-TRUTH.md`.

> **The race Dais demanded an answer for** (2026-06-03):
> *"Are you saying that automaton, Letta, Eliza, Virtuals, AgentKit — none
> of them have the skill to flexibly reply to emails and actually take
> actions on them? Tell me about that race."*
>
> **Honest answer:** No single OSS does it end-to-end. But **4 OSS each do
> a piece**, and gluing them with ~600 LOC produces the loop that doesn't
> exist as one project. This spec is the gluing.

| Field | Value |
|---|---|
| Spec ID | 08 |
| Status | DRAFT v1 (2026-06-03) |
| Authoritative for | inbox event ingest, context-aware reply, durable multi-step gig state, 24h followup, self-improvement from outcomes |
| Cross-refs | `06-PROJECT-TRACKING-HEARTBEAT.md` § 10 (v2 pivot), `07-HERMES-PIVOT.md` (L3 substrate), `00-MASTER.md` § 1 (4-layer arch) |

---

## § 0. The race result

Searched 2026-06-03 across ~30 OSS frameworks via parallel sub-agents:

| Tier | Frameworks investigated | Does end-to-end? |
|---|---|---|
| Workflow OSS | n8n, Dify, Flowise, Activepieces, Trigger.dev, Windmill, Inngest, Mastra, AnythingLLM | ✗ none have agent autonomy + email reply tracker combined |
| Autonomous agents 2025-26 | Suna (Kortix), OpenManus, Agno, AutoGen v2, CrewAI, claude-flow, OpenHands, SuperAGI, Letta, Restack | ✗ none have built-in inbox loop |
| Email-specific OSS | Inbox Zero (Elie), @keyid/agent-kit, Airut, Agentic-AI-Pipeline | △ **Inbox Zero has Reply Zero followup tracker = the missing piece**, but no project state machine |
| Production templates | claude-email-triage, Harvey, PipesHub, build-deploy-ai-agent, Llama3.2-LangGraph-Email-Agent | △ proof-of-concept stacks, none productionized for multi-project gig management |

Closed-source (= rejected per Dais's NHOSS-only rule): HumanLayer, Stable,
Lindy, Gumloop, Cognosys, Superhuman AI.

**The Inbox Zero finding overturns spec 06 v1.** Dais was right to push back —
I claimed the followup tracker was OSS-absent. It is not. It exists. Repo:
https://github.com/elie222/inbox-zero — feature literally named "Reply Zero:
Track emails to reply to and those awaiting responses" (verbatim from README).

---

## § 1. Architecture — 4 OSS + glue

```
                                                                                                     
   ┌─────────────────────────────────────────────────────────────────────────────────────────┐     
   │                                                                                         │     
   │            INBOUND EVENT (Gmail push / Slack webhook / GitHub mention / Lancers DM)     │     
   │                                          │                                              │     
   │                                          ▼                                              │     
   │            ┌────────────────────────────────────────────────────────────┐                │     
   │            │  HERMES AGENT DAEMON  (~/.local/bin/hermes, 24/7)            │                │     
   │            │   - receives webhook via slack-bridge skill                  │                │     
   │            │   - FTS5 memory query: "is this thread known?"               │                │     
   │            │   - emits event into Mastra graph                            │                │     
   │            └────────────────────────────────────────────────────────────┘                │     
   │                                          │                                              │     
   │                                          ▼                                              │     
   │            ┌────────────────────────────────────────────────────────────┐                │     
   │            │  INBOX ZERO (fork)  anicca-oss/services/inbox-zero/        │                │     
   │            │   - Gmail Push (Pub/Sub) primary trigger                    │                │     
   │            │   - AI Assistant rule engine (classify / archive / draft)   │                │     
   │            │   - Reply Zero tracker (DB: replied_threads, awaiting_them)│                │     
   │            │   - Multi-identity (Dais's gmail + Anicca's agentmail)      │                │     
   │            └────────────────────────────────────────────────────────────┘                │     
   │                                          │                                              │     
   │                          ┌───────────────┴───────────────┐                              │     
   │                          ▼                               ▼                              │     
   │            (existing project?)                  (new project?)                          │     
   │                          │                               │                              │     
   │                          ▼                               ▼                              │     
   │   ┌─────────────────────────────────┐    ┌─────────────────────────────────┐           │     
   │   │ MASTRA GRAPH (resumed)            │    │ MASTRA GRAPH (new instance)     │           │     
   │   │ anicca-oss/runtime/mastra-graphs/│    │ workflow archetype picked by    │           │     
   │   │   gig-application.ts              │    │ classifier (gig / issue /       │           │     
   │   │   github-issue.ts                 │    │ outreach / customer-thread)     │           │     
   │   │   customer-thread.ts              │    └─────────────────────────────────┘           │     
   │   │   cold-outreach.ts                │                                                  │     
   │   │                                   │                                                  │     
   │   │ - suspend("wait 24h for reply")  │                                                  │     
   │   │ - suspend("wait until PR merged")│                                                  │     
   │   │ - suspend("wait until invoice $$")│                                                  │     
   │   │ - resumes after restart           │                                                  │     
   │   └─────────────────────────────────┘                                                   │     
   │                          │                                                              │     
   │                          ▼                                                              │     
   │   ┌─────────────────────────────────────────────────────────────────┐                  │     
   │   │ DRAFT  (Claude/Kimi via Anthropic subscription or OpenRouter)    │                  │     
   │   │   - project context loaded from projects + project_events       │                  │     
   │   │   - relationship memory loaded from Hermes FTS5                  │                  │     
   │   │   - relevant skill examples loaded from skills_used past         │                  │     
   │   └─────────────────────────────────────────────────────────────────┘                  │     
   │                          │                                                              │     
   │                          ▼                                                              │     
   │   ┌─────────────────────────────────────────────────────────────────┐                  │     
   │   │ JUDGE  (recursive-improver pattern, ~3 critic agents)            │                  │     
   │   │   - is this reply useful?                                         │                  │     
   │   │   - does it advance the project?                                  │                  │     
   │   │   - does it match the relationship tone?                          │                  │     
   │   │   - does it contain hallucinated facts?                           │                  │     
   │   └─────────────────────────────────────────────────────────────────┘                  │     
   │                          │                                                              │     
   │                          ▼                                                              │     
   │   ┌─────────────────────────────────────────────────────────────────┐                  │     
   │   │ ACT  via COMPOSIO + custom adapters                              │                  │     
   │   │   anicca-oss/adapters/composio/                                  │                  │     
   │   │   - composio.gmail.send_email                                    │                  │     
   │   │   - composio.slack.post_message                                  │                  │     
   │   │   - composio.linear.create_issue                                 │                  │     
   │   │   - composio.github.create_pr                                    │                  │     
   │   │   anicca-oss/adapters/custom/                                    │                  │     
   │   │   - lancers.send_message  (custom — not in Composio yet)         │                  │     
   │   │   - coconala.send_message (custom)                               │                  │     
   │   │   - bland.ai.outbound_call (custom)                              │                  │     
   │   │   - agentmail.send         (custom)                              │                  │     
   │   └─────────────────────────────────────────────────────────────────┘                  │     
   │                          │                                                              │     
   │                          ▼                                                              │     
   │   ┌─────────────────────────────────────────────────────────────────┐                  │     
   │   │ TRACK  → projects.next_action_at = NOW + 24h                     │                  │     
   │   │       → project_events += row("sent_reply", payload)             │                  │     
   │   │       → Reply Zero.awaiting_them += thread_id                    │                  │     
   │   └─────────────────────────────────────────────────────────────────┘                  │     
   │                          │                                                              │     
   │                          ▼                                                              │     
   │   ┌─────────────────────────────────────────────────────────────────┐                  │     
   │   │ MASTRA WAIT 24h                                                   │                  │     
   │   │   - if reply arrives    → graph resumes at next node              │                  │     
   │   │   - if 24h timeout      → fire re-ping subgraph (= polite nudge)  │                  │     
   │   │   - if 7d timeout       → mark project stalled, notify Dais       │                  │     
   │   └─────────────────────────────────────────────────────────────────┘                  │     
   │                          │                                                              │     
   │                          ▼                                                              │     
   │   ┌─────────────────────────────────────────────────────────────────┐                  │     
   │   │ LEARN  on graph completion (success OR fail)                     │                  │     
   │   │   - delta = actual_outcome vs predicted_outcome                  │                  │     
   │   │   - write Hermes FTS5 memory row: lesson + tags + project_type   │                  │     
   │   │   - next graph instance loads similar past lessons at entry      │                  │     
   │   └─────────────────────────────────────────────────────────────────┘                  │     
   │                                                                                         │     
   └─────────────────────────────────────────────────────────────────────────────────────────┘     
                                                                                                     
```

---

## § 2. Component spec — what each piece owns

### § 2.1 Hermes Agent (= existing, no install needed)

| Owns | Path |
|---|---|
| 24/7 daemon process | `/Users/operator/.local/bin/hermes` (v0.12.0 installed) |
| FTS5 memory across messages + sessions | `~/.hermes/state.db` |
| Skill registry (read + write own) | `~/.hermes/skills/` |
| Slack / Telegram / Discord gateway | existing `slack-bridge` + adapters |
| Cron schedule for re-ping nudges | Hermes' built-in scheduler |

Hermes does **NOT** own: Gmail watching (that's Inbox Zero), durable
workflow state (that's Mastra), action adapters (that's Composio).

### § 2.2 Inbox Zero fork (= the email loop reference)

| Owns | Path |
|---|---|
| Gmail OAuth + Push subscription | `anicca-oss/services/inbox-zero/apps/web/` |
| AI Assistant rule engine | upstream Elie code |
| Reply Zero followup tracker | upstream Elie code (= the part I claimed didn't exist) |
| Multi-identity support | `accounts` table |
| Bulk unsubscriber (free win) | upstream |

Fork strategy:
- `git submodule add` upstream into `anicca-oss/services/inbox-zero/`
- Pin to specific tag
- Override `lib/ai/handle-rule.ts` to emit Mastra event instead of direct LLM call
- Override `lib/db/schema.ts` to use Conway SQLite via shim (Inbox Zero uses Postgres)
- Keep upstream's UI for Dais's personal Gmail (= free productivity for Dais)
- Use programmatic API for Anicca's agentmail inbox (= no UI needed)

### § 2.3 Mastra (= durable workflow per project archetype)

| Owns | Path |
|---|---|
| Workflow definitions per archetype | `anicca-oss/runtime/mastra-graphs/*.ts` |
| Suspend / resume primitive | `mastra.workflow.suspend({reason, resumeAt})` |
| State storage (Conway state.db shim) | adapter we write |
| Agent ReAct loops within nodes | Mastra's `agent` primitive |

Archetypes to ship in v1:
- `gig-application.ts` (= Lancers/Coconala/Upwork gig flow)
- `github-issue.ts` (= bounty hunting)
- `customer-thread.ts` (= existing relationship maintenance)
- `cold-outreach.ts` (= prospecting)

### § 2.4 Composio + custom adapters

| Owns | Path |
|---|---|
| Generic SaaS adapters (Gmail / Slack / Linear / GitHub / X) | npm install + config |
| Lancers JP adapter | `anicca-oss/adapters/custom/lancers/` |
| Coconala JP adapter | `anicca-oss/adapters/custom/coconala/` |
| Bland.ai voice call | `anicca-oss/adapters/custom/bland/` |
| AgentMail send | `anicca-oss/adapters/custom/agentmail/` |

### § 2.5 Conway state.db (= reused)

| Table | Purpose |
|---|---|
| `projects` | 1 row per long-running thing — gig / issue / thread / outreach |
| `project_events` | timeline of every event touching a project |
| `relationships` | 1 row per counterparty — name / company / past_interactions / preferred_tone |
| `inbox_zero_threads` (shim) | Inbox Zero's threads table mapped to SQLite |
| `mastra_workflow_runs` | Mastra's resumable state checkpoints |
| `hermes_fts5_memories` | Hermes' existing learning store |

Joined view `v_active_projects` materializes the "what does Anicca owe whom"
dashboard — replaces v1's `anicca-project-sweep` cron.

---

## § 3. The glue we write (= ~600 LOC, NOT a from-scratch system)

| Module | LOC | Purpose |
|---|---|---|
| `anicca-oss/services/inbox-zero-shim/sqlite-adapter.ts` | ~120 | Inbox Zero's Postgres queries → Conway SQLite |
| `anicca-oss/services/inbox-zero-shim/event-emitter.ts` | ~80 | When Inbox Zero AI Assistant fires a rule, emit Mastra event instead of replying directly |
| `anicca-oss/runtime/mastra-graphs/gig-application.ts` | ~150 | Multi-step gig graph with suspend-points |
| `anicca-oss/runtime/mastra-graphs/github-issue.ts` | ~80 | GitHub bounty graph |
| `anicca-oss/runtime/mastra-graphs/customer-thread.ts` | ~60 | Customer relationship graph |
| `anicca-oss/runtime/mastra-graphs/cold-outreach.ts` | ~50 | Prospecting graph |
| `anicca-oss/runtime/learn-from-outcome.ts` | ~60 | At graph end → write Hermes FTS5 lesson |
| `anicca-oss/adapters/custom/lancers/index.ts` | ~150 | Lancers DM + bid + message + project status |
| `anicca-oss/adapters/custom/coconala/index.ts` | ~150 | Coconala equivalents |
| **Total** | **~900** | (= still well under "a new framework") |

Custom adapters end up longer because the JP platforms have no OSS clients.
The orchestration glue itself is ~600 LOC.

---

## § 4. Bootstrap order (= "do it now" sequence)

| Step | What | Done by |
|---|---|---|
| 1 | Fork Inbox Zero into `anicca-oss/services/inbox-zero/` | git submodule |
| 2 | Inbox Zero `pnpm i && pnpm dev` local — OAuth Dais's gmail | manual once |
| 3 | Install Mastra: `cd anicca-oss/runtime && pnpm i @mastra/core` | npm |
| 4 | Install Composio: `cd anicca-oss && pnpm i @composio/core` | npm |
| 5 | Write SQLite shim for Inbox Zero | 1 subagent (1 hour) |
| 6 | Write gig-application Mastra graph | 1 subagent (1 hour) |
| 7 | Wire Inbox Zero rule → Mastra event | 1 subagent (30 min) |
| 8 | Compose first E2E test: real Lancers email → reply → 24h timer | manual verify |
| 9 | Add github-issue + customer-thread graphs | parallel subagents |
| 10 | Add Lancers + Coconala custom adapters | parallel subagents |

Phase 1 (steps 1-8) = a single afternoon of work. Phase 2 (steps 9-10)
parallelize cleanly.

---

## § 5. Verification gates

| Gate | Evidence |
|---|---|
| G1 — Inbox Zero up | `curl http://localhost:3000/api/health` returns 200, Gmail OAuth complete, push subscription active. |
| G2 — Reply Zero ground truth | Send test email → reply from second account → `replied_threads` table has correct row within 60s. |
| G3 — SQLite shim works | All Inbox Zero core queries (`findUnique`, `create`, `update` on `Thread`, `Message`, `Rule`) succeed against Conway state.db. |
| G4 — Mastra graph durable | Suspend `gig-application` at "wait 24h" → `kill -9 $(pgrep -f mastra)` → restart → workflow continues from same step. |
| G5 — Composio Gmail send | `composio call gmail.send_email --to=... --body=...` returns 200, email arrives. |
| G6 — E2E Lancers gig | Fake Lancers email → Anicca drafts reply with project context loaded → judges pass → sends → 24h later if no reply, re-ping subgraph fires automatically. All recorded in `projects` + `project_events` + Reply Zero. |
| G7 — Self-improvement edge | After 5 completed graphs of same archetype, the 6th instance's entry node loads 3+ prior lessons via Hermes FTS5 and references them in the draft prompt. |

---

## § 6. Anti-goals (= what this spec does NOT try to do)

- **Not a from-scratch agent framework.** Hermes already exists. Mastra
  exists. Composio exists. Inbox Zero exists. We compose.
- **Not a UI.** Inbox Zero ships a Next.js UI; we use it as-is for Dais's
  inbox. No new UI work in v1.
- **Not Telegram/WhatsApp gateway.** Hermes already does that via
  `slack-bridge` and adapters. Stays orthogonal.
- **Not a replacement for `anicca-mr-bot`** (calls, wake events,
  lateness guard). That's a separate orchestration plane — physical world,
  not inbox.
- **Not multi-tenant SaaS.** This is single-Anicca-instance. The NHOSS
  colony pattern (= one Anicca per host) is in `05-SERVER-NATIVE-DEPLOY.md`.

---

## § 7. Where this falls short of what Dais wants

| Dais wants | This spec gives | Gap to close in v2 |
|---|---|---|
| "monitor TikTok views of MY post + iterate next post" | nothing — out of scope (this is `02-IMITATE-AND-COOK.md`'s job) | wire TikTok analytics adapter into Mastra graph `content-iteration.ts` |
| "reply in <5 min after inbound" | <60s with Gmail push, but Lancers polling is 5-min cron interval | reverse-engineer Lancers websocket or use Browserbase persistent session |
| "no human in loop" | Inbox Zero default has "Draft + manual approve" mode; we override to direct-send for Anicca's own inbox, keep approve mode for Dais's inbox | document the policy clearly per-identity |
| "self-improve like a human worker" | learn-from-outcome.ts writes lessons; entry node reads them | add a "weekly self-review" Mastra graph that summarizes lessons + edits the archetype prompts directly |

---

## § 8. Changelog

| Date | Change |
|---|---|
| 2026-06-03 | Initial draft. Born from Dais's race call exposing that I hadn't searched deeply enough. Stack: Inbox Zero (Reply Zero tracker) + Mastra (durable suspend/resume) + Composio (adapters) + Hermes (daemon) + Conway state.db (reuse). ~600 LOC of glue, not a from-scratch build. |
