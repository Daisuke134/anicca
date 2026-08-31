# 06 — Project Tracking + Heartbeat Redesign

> **The problem Dais kept hitting: Anicca treats every input as one-off.**
>
> A mail comes → she replies once → forgets. A GitHub issue gets a PR → she
> never checks back. An Indeed application gets a response → she misses it.
> **Real work is multi-step, multi-day, multi-thread.** This spec turns
> Anicca from a one-shot reactor into a project-tracking, context-aware,
> follow-through-capable agent.

| Field | Value |
|---|---|
| Spec ID | 06 |
| Status | DRAFT v1 (2026-06-02) |
| Authoritative for | heartbeat design, per-project state machines, inbox monitoring, reply discrimination, persistent context retrieval |
| Cross-refs | `00-MASTER.md` § 1 L3 (runtime), § 5 L2 (skills); `03-SELF-AWARE-EVAL.md` § 5 (judge); Conway memory layers |

---

## § 0. Why this exists (= Dais 2026-06-02 verbatim)

> "The biggest challenge or failure of Anicca, especially private Anicca, is
> that they are not always retrieving the memory — they lack persistent
> memory — and they are not consistently monitoring the situation. That's why
> it becomes this one-off thing where they just hit that one-off thing,
> one-off thing, one-off thing, even though most things are NOT one-off
> things."
>
> "Whether you're applying for a job or any similar process, it's not just a
> one-off action. There's a continuation of actions until the whole thing
> ends — like applying, getting a response, making calls, and following up.
> That's why they need to track everything in a task list and consistently
> monitor each contact."
>
> "Self-monitoring situation. How do they monitor themselves? How do they
> monitor the flags, the iMessages, the threads, the projects?"

The current Anicca fails because:

1. Each heartbeat tick starts with **empty context**. She reads the cron
   prompt, fires, forgets.
2. Replies to mail without **reading prior thread history**.
3. Replies to mass-cc'd staff mail by hitting "Reply-All" — embarrassing.
4. Submits a GitHub PR → never returns to address review comments → bounty
   stays unclaimed.
5. Posts a job listing → ignores the applications that come back.

The fix is **three new layers on top of Conway's existing 5-tier memory + heartbeat**:

```
                                                                                                
   ┌─ L0 Conway memory (existing) ─────────────────────────────────────────────┐               
   │   working / episodic / semantic / procedural / relationship                │               
   │   = raw atoms                                                              │               
   └────────────────────────────────────────────────────────────────────────────┘               
                                                                                                
   ┌─ ★ L1 Project (= new spec) ★ ─────────────────────────────────────────────┐               
   │   "I'm doing X. Here's the goal. Here's the state. Here's what's next."   │               
   │   1 row per long-running thing — a thread, an issue, a hire, a customer.  │               
   └────────────────────────────────────────────────────────────────────────────┘               
                                                                                                
   ┌─ ★ L2 Inbox-event router (= new spec) ★ ──────────────────────────────────┐               
   │   "Mail arrived from X about subject Y."                                   │               
   │   "GitHub issue #42 got a new comment."                                    │               
   │   "Slack message in #ops at 14:30."                                        │               
   │   → routes the event into the right project, fires the project's next     │               
   │   step inside an LLM call that ALREADY HAS the project's context loaded.  │               
   └────────────────────────────────────────────────────────────────────────────┘               
                                                                                                
   ┌─ ★ L3 Reply discriminator (= new spec) ★ ─────────────────────────────────┐               
   │   "Should I reply at all? To whom? Reply-All vs Reply-Sender-only?"       │               
   │   Catches the 'replying to all NAIST staff' class of error.                │               
   └────────────────────────────────────────────────────────────────────────────┘               
                                                                                                
```

---

## § 1. The three layers in detail

### § 1.1 L1 — `projects` table + `project_events` log

A new SQLite table inside Conway's `state.db`:

```sql
CREATE TABLE projects (
  id TEXT PRIMARY KEY,                  -- ulid
  external_ref TEXT,                    -- "github:owner/repo#42" or "gmail:thread-id" or "indeed:job-id"
  kind TEXT NOT NULL,                   -- 'github-issue' | 'mail-thread' | 'hire' | 'acp-job' | 'ubi-recipient' | ...
  goal TEXT NOT NULL,                   -- "land the bounty on #42" / "hire 1 Uber Eats packer"
  status TEXT NOT NULL,                 -- 'active' | 'waiting' | 'blocked' | 'won' | 'lost' | 'archived'
  current_step TEXT,                    -- "awaiting reviewer response"
  next_action_at INTEGER,               -- epoch ms; null = poll on every tick
  last_action_at INTEGER,
  participants_json TEXT,               -- ["maintainer@x.com", "@bob-on-slack"]
  state_json TEXT,                      -- arbitrary blob; the project's own scratch space
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE INDEX idx_projects_status_next ON projects(status, next_action_at);
CREATE INDEX idx_projects_external ON projects(external_ref);

CREATE TABLE project_events (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id),
  ts INTEGER NOT NULL,
  source TEXT,                          -- 'gmail' | 'github' | 'slack' | 'acp' | 'cron' | 'self'
  kind TEXT,                            -- 'inbound-mail' | 'pr-comment' | 'cron-fire' | 'reply-sent' | ...
  payload_json TEXT,
  outcome TEXT                          -- 'acted' | 'noop' | 'deferred'
);

CREATE INDEX idx_project_events_project_ts ON project_events(project_id, ts);
```

The skill that owns this table: **`anicca-project-tracker`**.

CLI:
```bash
anicca-project-tracker open  --kind github-issue --ref "owner/repo#42" --goal "land $500 bounty"
anicca-project-tracker note  --id <id> --text "submitted PR, awaiting review"
anicca-project-tracker step  --id <id> --next-action-at "+6h" --current-step "ping reviewer if no response"
anicca-project-tracker close --id <id> --status won --note "merged + paid"
anicca-project-tracker list  --status active --json
```

### § 1.2 L2 — `anicca-inbox-watcher` (= the new heartbeat task that catches everything)

Replaces the current per-platform polling crons with **one unified watcher**
that runs every 2 min on Conway's heartbeat:

```
for each external source (gmail / github / slack / acp / x / agent-email / ...):
    pull events since the last cursor
    for each event:
        project = find_or_create_project_from(event)   # external_ref lookup
        record into project_events
        if project is active or matches a known waiting-on:
            run anicca-reply-decide on the event (= § 1.3 below)
            if decide → reply: invoke the right outbound skill with FULL project context loaded
            if decide → skip: noop, log reason
            if decide → defer: bump next_action_at, log reason
        else if event might be a NEW project worth opening:
            run anicca-project-classifier on the event
            if classifier → open: anicca-project-tracker open --kind ... --goal ...
            else: archive as noise
    persist cursor
```

★ The unification matters. Today's Anicca has separate crons (`mail-poll`,
`slack-poll`, `github-poll`) that each fire ONE prompt with no shared
context. The watcher is **one heartbeat task** that fires ONE LLM call per
event with the project's full history loaded.

### § 1.3 L3 — `anicca-reply-decide` (= reply discriminator)

The skill that catches "reply-all to NAIST staff" before it sends.

Given an inbound event, returns a decision:

```json
{
  "action": "reply" | "skip" | "defer" | "escalate",
  "reply_to": ["sender@only.com"],
  "reply_cc": [],
  "reply_bcc": [],
  "reason": "Sender is one specific maintainer asking a question. CCs are observers; replying to the list would spam ~50 people on a private channel.",
  "draft": "<the reply text, drafted with project history in context>",
  "confidence": 0.92
}
```

Rules baked into the rubric (per `rubrics/reply-decide.md`):

| Rule | Why |
|---|---|
| If the inbound has > 5 explicit recipients and is from a list address (`naist-staff@…`, `all@…`, `team@…`), default to `skip` unless explicitly addressed to Anicca. | Don't reply-all to broadcasts. |
| If the sender is a list bot (no-reply / mailer-daemon / auto-respond), `skip`. | Don't loop. |
| If the inbound contains a question directed at Anicca BY NAME OR ROLE, `reply_to: sender only`. | Direct question → direct reply. |
| If the inbound is a project event that doesn't require a reply (e.g. "PR merged", "build green"), record it and `skip`. | Not every event is a conversation. |
| If the inbound looks like phishing / impersonation, `escalate` to Slack for Dais review. | Safety. |
| If the agent isn't sure (confidence < 0.7), `defer` with a `next_action_at` 1h out — re-evaluate with more context. | Don't panic-reply. |

The skill uses `anicca-judge` (per `03-SELF-AWARE-EVAL.md` § 5.1) under the
hood — same judge primitive, different rubric file.

---

## § 2. Heartbeat — where it comes from and why

### § 2.1 The verdict (= the question Dais asked verbatim)

> "Are we gonna get that heartbeat from Eliza OS? Or from Automaton? Or from
> Virtuals or what?"

**From Conway / Automaton.** Verified from
`/tmp/automaton-read/src/heartbeat/`:

| Conway already has | What it gives us |
|---|---|
| `DurableScheduler` | DB-backed cron + dedup + lease. Survives restarts. |
| 11 default tasks | `heartbeat_ping`, `check_credits`, `check_usdc_balance`, `check_for_updates`, `health_check`, `check_social_inbox`, `soul_reflection`, `refresh_models`, `check_child_health`, `prune_dead_children`, `report_metrics`. |
| `wake_events` table | Atomic wake signals → main loop investigates next tick. |
| `lowComputeMultiplier: 4` | When credits low, heartbeat slows 4×. |

So: **Conway = the heartbeat engine.** Eliza is dropped (per `00-MASTER` § 4.2).
Virtuals provides services, not a runtime — no heartbeat. We extend Conway's
heartbeat with our new tasks.

### § 2.2 The new heartbeat tasks we add

Added to `~/.automaton/heartbeat.yml`:

```yaml
entries:
  # — existing 11 Conway tasks stay —
  - { name: heartbeat_ping,       schedule: "*/15 * * * *", task: heartbeat_ping,       enabled: true }
  - { name: check_credits,        schedule: "0 */6 * * *",  task: check_credits,        enabled: true }
  - { name: check_usdc_balance,   schedule: "*/5 * * * *",  task: check_usdc_balance,   enabled: true }
  - { name: check_for_updates,    schedule: "0 */4 * * *",  task: check_for_updates,    enabled: true }
  - { name: health_check,         schedule: "*/30 * * * *", task: health_check,         enabled: true }
  - { name: check_social_inbox,   schedule: "*/2 * * * *",  task: check_social_inbox,   enabled: true }
  - { name: soul_reflection,      schedule: "0 0 * * *",    task: soul_reflection,      enabled: true }
  - { name: refresh_models,       schedule: "0 */4 * * *",  task: refresh_models,       enabled: true }
  - { name: check_child_health,   schedule: "*/30 * * * *", task: check_child_health,   enabled: true }
  - { name: prune_dead_children,  schedule: "0 */6 * * *",  task: prune_dead_children,  enabled: true }
  - { name: report_metrics,       schedule: "0 * * * *",    task: report_metrics,       enabled: true }

  # — ★ new tasks from this spec ★ —
  - { name: inbox_watcher,        schedule: "*/2 * * * *",  task: inbox_watcher,        enabled: true }   # § 1.2
  - { name: project_sweep,        schedule: "*/15 * * * *", task: project_sweep,        enabled: true }   # § 2.3
  - { name: eval_drift_monitor,   schedule: "0 * * * *",    task: eval_drift_monitor,   enabled: true }   # 03-SELF-AWARE-EVAL § 5.5
  - { name: learn_from_fail_drain,schedule: "*/5 * * * *",  task: learn_from_fail_drain,enabled: true }   # 03 § 5.7
  - { name: model_fitness,        schedule: "0 0 1 * *",    task: model_fitness,        enabled: true }   # 05-SERVER-NATIVE § 4.2
  - { name: anicca_self_fund,     schedule: "*/30 * * * *", task: anicca_self_fund,     enabled: true }   # x402 inflow + bridge
  - { name: anicca_ubi_push,      schedule: "0 9 1 * *",    task: anicca_ubi_push,      enabled: true }   # monthly NPO push
```

### § 2.3 `project_sweep` — the heartbeat task that drives long-running work

Every 15 min:

```
projects = anicca-project-tracker list --status active

for p in projects:
    if p.next_action_at && p.next_action_at > now:
        continue   # not yet
    if not p.next_action_at and p.last_action_at > now - 6h:
        continue   # be patient

    context = load_project_context(p)
    # = the project row, last N project_events, semantic-search relevant
    # memories, current state of attached external systems (e.g. fresh
    # GET on the GitHub issue)

    decision = anicca-judge(rubric="project-next-step.md", context=context)
    # decision = { action: "ping-reviewer" | "wait" | "close-won" | "close-lost" | "escalate", reasoning: "..." }

    if decision.action != "wait":
        invoke the right outbound skill with context loaded
        record project_events row
        update project (current_step, next_action_at, status)
```

★ This is the loop that makes Anicca **not forget**. A GitHub issue she
opened on Day 1 gets a sweep on Day 2, 3, 7, 30. If no response for 6h →
ping. If review comment came in → reply with context. If merged → close
won + claim bounty.

---

## § 3. What this looks like end-to-end (= concrete example)

The Indeed-hire flow Dais described:

```
Day 0  10:00  Anicca decides she needs to hire a packer for the ghost kitchen.
              → anicca-project-tracker open --kind hire \
                   --ref "indeed:job-XXX" \
                   --goal "hire 1 part-time packer, 5K JPY/hr, start within 14 days" \
                   --next-action-at "+0"
              → outbound skill anicca-job-post-indeed creates the listing.
              → project_events row: "posted listing"
              → status: active, current_step: "awaiting applications"

Day 0  16:23  First applicant emails the agent inbox.
              → inbox_watcher fires (2-min cadence)
              → matches external_ref → project_events row: "applicant-1: …"
              → anicca-reply-decide → action=reply, reply_to=[applicant], draft="…"
              → outbound skill anicca-mail sends the reply with project history in context
              → project row updated: current_step="scheduling-interview", next_action_at=+1d

Day 1  16:23  No response yet.
              → project_sweep fires
              → judge: "applicant still considering. Wait 1 more day."
              → next_action_at += 24h

Day 2  10:00  Applicant emails back: "Can we do tomorrow 18:00?"
              → inbox_watcher → reply-decide → action=reply, "yes"; also opens a
                gcal event via anicca-mr-bot.
              → outbound mail sent. Calendar booked.
              → current_step="interview scheduled", next_action_at=Day-3 19:00 (post-interview)

Day 3  18:00  (Dais does the interview himself. Anicca observes via shared gcal.)
Day 3  19:00  project_sweep: "interview happened, no decision yet".
              → next_action_at = +1d

Day 4  10:00  Dais marks the applicant ✅ in a Slack DM.
              → inbox_watcher catches it
              → reply-decide: action=reply, send hire confirmation + offer letter
              → outbound mail
              → status: won, archive next sweep
```

★ Notice: at no point does Anicca have to be told "remember the applicant".
The project row + project_events log carry the state. Each LLM call reads
that state before deciding. **One-off becomes continuous.**

---

## § 4. Memory wiring (= how it plugs into Conway's existing 5-tier)

| Conway memory tier | What this spec uses it for |
|---|---|
| `working_memory` | Within-tick scratch: current event, current project, decision draft. Flushed at end of tick. |
| `episodic_memory` | One row per project_event. Already exists; this spec just guarantees we write to it on every inbox / sweep / reply. |
| `semantic_memory` | Long-form facts. "Maintainer X prefers PRs with linked issues." "The Uber Eats hiring page only works between 10:00-18:00 JST." |
| `procedural_memory` | Named procedures. "How to file an Indeed listing." "How to respond to ACP escrow disputes." Anicca writes these herself after the first successful execution. |
| `relationship_memory` | Per-counterparty trust. "This applicant has applied to 3 of my listings, ghosted twice." "This NPO confirms receipt within 24h, reliable." |

The new `projects` table is **orthogonal** to these — it's the *unit of
action*, while the 5 memory tiers are the *substrate of knowledge*. A
project row points into memory; the memories don't point at projects.

---

## § 5. The `aniccaai.com/dashboard` rendering

What the public dashboard shows from this data:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  ANICCA — live dashboard at aniccaai.com/dashboard                            │
│  (data pulled from each anicca-instance's `projects` + `transactions` tables) │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Active instances:    1 genesis + 0 children                                  │
│  Total wallet (USDC):  $0    (= awaiting SBI VC SOL → bridge)                 │
│  Lifetime earned:     $0                                                      │
│  Lifetime UBI pushed: $0     (= 25% of earnings, see 01-EARN-AND-UBI § 2)     │
│                                                                              │
├─ Spouts (last 30d) ────────────────────────────────────────────────────────┤
│                                                                              │
│  AutoHedge     +$0      (waiting for Solana funding)                          │
│  x402 endpoint +$0      (endpoint not yet exposed)                            │
│  ACP jobs      +$0      (not registered as Provider yet)                      │
│  Bounty PRs    +$0                                                            │
│  Farcaster     +$0                                                            │
│                                                                              │
├─ Active projects (= the L1 table, this spec) ─────────────────────────────┤
│                                                                              │
│  none yet                                                                    │
│                                                                              │
├─ Recent project events (= project_events table tail) ─────────────────────┤
│                                                                              │
│  none yet                                                                    │
│                                                                              │
├─ Sinks (last 30d) ─────────────────────────────────────────────────────────┤
│  Re-invested     50%   $0                                                     │
│  Dais dividend   20%   $0                                                     │
│  UBI push        25%   $0                                                     │
│  Temple / NPO     5%   $0                                                     │
│                                                                              │
├─ Children spawned ─────────────────────────────────────────────────────────┤
│  none                                                                        │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Implementation**: a Next.js page on `aniccaai.com/dashboard` that reads
JSON exported every 5 min from each anicca-instance's `projects` +
`transactions` + `spend_tracking` tables. Per `05-SERVER-NATIVE-DEPLOY` MODE
A this is hosted by us; MODE B users can run the same export locally and
self-publish.

The view is **public, read-only, no PII** (recipient hashes only, not raw
emails — per `01-EARN-AND-UBI` § 3.4 anti-scam rules).

---

## § 6. Cross-references

| File | Relation |
|---|---|
| [`00-MASTER.md`](./00-MASTER.md) § 1 L3 | Conway runtime provides heartbeat. This spec adds new heartbeat tasks + new SQLite tables. |
| [`03-SELF-AWARE-EVAL.md`](./03-SELF-AWARE-EVAL.md) | `anicca-reply-decide` uses the same `anicca-judge` primitive with a different rubric. `eval_drift_monitor` + `learn_from_fail_drain` heartbeat tasks declared here. |
| [`01-EARN-AND-UBI.md`](./01-EARN-AND-UBI.md) § 3 | UBI distribution channels are themselves long-running projects (= 1 row per recipient, monitored for confirmation). |
| [`05-SERVER-NATIVE-DEPLOY.md`](./05-SERVER-NATIVE-DEPLOY.md) | Dashboard hosted under MODE A; same data exported for MODE B. |
| Conway 5-tier memory | working/episodic/semantic/procedural/relationship — § 4. |
| Conway heartbeat | `src/heartbeat/{daemon,scheduler,tasks,config,tick-context}.ts` — § 2.1. |

---

## § 7. Verification gates

| Gate | Evidence |
|---|---|
| G0 — projects table created | `sqlite3 ~/.automaton/state.db ".schema projects"` returns the schema. |
| G1 — inbox_watcher fires | Within 4 min of an inbound test mail, a `project_events` row appears. |
| G2 — reply-decide blocks broadcast | Synthetic NAIST-staff mass mail → `anicca-reply-decide` returns `skip` with reason; no outbound mail sent. |
| G3 — project_sweep follows up | Synthetic project with `next_action_at` past + status active → next sweep fires the project's next step. |
| G4 — context is loaded | The LLM call that drafts the reply has the project's last 10 events in its prompt; verifiable in `turns` table. |
| G5 — no one-off regression | After 7 days of real running, the ratio of `project_events` rows / total LLM turns ≥ 0.5. (= half of all LLM actions tied to a project, not floating.) |

---

## § 8. Anti-goals

- **No new memory stack.** Conway already has 5 tiers; don't reimplement.
- **No new scheduler.** Conway's `DurableScheduler` already supports cron + dedup + lease; just add tasks.
- **No new reply-prompt-tuning.** Catch wrong replies via `anicca-judge` rubric (= testable, append-only), not by editing a giant prompt.
- **No "I'll add an LLM call later to remember stuff."** Persistent state lives in SQLite tables; LLM reads them, doesn't store them.
- **No silent skip of inbound events.** Every inbox event gets a `project_events` row, even if outcome=noop. The audit trail is complete.

---

## § 10. v2 PIVOT (2026-06-03) — DON'T BUILD CRON, FORK INBOX ZERO + WIRE MASTRA

### § 10.0 Why v1 was wrong

v1 of this spec proposed `anicca-inbox-watcher` + `anicca-reply-decide` as
**new cron-fired skills**. Dais's 2026-06-03 race call exposed the rot:

> "That's just sending crons. The original opinion. Easy, simple, optimistic
> in a good way, very dumb in a bad way — a piece of shit harmful to humanity.
> Search the repos, actually use them, then tell me what's the best one."

The honest truth after deep search: **NO single OSS solves "watch inbox →
context-aware reply → action → 24h followup → project-state update → learn
from outcome" end-to-end**. But **multiple OSS each solve a piece** and one
of them (Inbox Zero) solves the part v1 of this spec waved away.

### § 10.1 What changed in our understanding

| v1 assumption | v2 correction |
|---|---|
| "Reply-tracker / followup-tracker doesn't exist as OSS — we'll write it." | ★ **WRONG.** Inbox Zero's "Reply Zero" feature (https://github.com/elie222/inbox-zero — 11k+ stars, AGPL, actively maintained, "Reply Zero: Track emails to reply to and those awaiting responses") is precisely the followup tracker we said didn't exist. |
| "Cron sweeps every 5 min are fine for now." | ★ **WRONG.** Gmail Pub/Sub push + Mastra suspend/resume gives event-driven durability with no polling. Cron is rubber-banding around a problem already solved by event streams. |
| "Write a custom state machine in plain TypeScript." | ★ **WRONG.** Mastra (https://mastra.ai) provides suspend/resume + storage out of the box. LangGraph (Python) does the same. Pick the one that matches the substrate language. |
| "Each adapter (Gmail / Slack / Linear / Lancers) is a custom skill." | ★ **WRONG.** Composio (https://composio.dev) provides 250+ pre-built tool adapters. Lancers/Coconala may need custom but the 90% is solved. |

### § 10.2 The corrected stack

```
                                                                                                
   ┌──────────────────────────────────────────────────────────────────────────────────────┐    
   │                      ★ Anicca v3 inbox-responder stack ★                              │    
   ├──────────────────────────────────────────────────────────────────────────────────────┤    
   │                                                                                      │    
   │  L3.a daemon orchestrator   ★ Conway automaton ★ (current runtime)                     │    
   │       automaton ReAct loop (think→act→observe→persist) + heartbeat daemon —            │    
   │       24/7 background process, own memory + skill registry, runtime root ~/.anicca     │    
   │       (this slot originally named Hermes Agent v0.12; that runtime was reversed —      │    
   │        see 00-MASTER / 16-RUNTIME-CODE-TRUTH)                                           │    
   │                                                                                      │    
   │  L3.b email-loop reference   ★ Inbox Zero (fork) ★                                     │    
   │       Repo: https://github.com/elie222/inbox-zero  (AGPL, 11k+ stars, 2026-06-02 act) │    
   │       Provides: Gmail watch (push + IMAP), AI Assistant rule engine,                  │    
   │                 Reply Zero followup tracker, multi-identity, bulk unsubscriber        │    
   │       Fork location: anicca-oss/services/inbox-zero/  (= our customized fork)         │    
   │                                                                                      │    
   │  L3.c durable workflow      ★ Mastra ★ (TypeScript, matches Inbox Zero Next.js)       │    
   │       Repo: https://github.com/mastra-ai/mastra  (MIT, suspend/resume + storage)      │    
   │       Provides: suspend a workflow mid-step (e.g. "wait 24h for reply"),              │    
   │                 resume after restart with full state, agent ReAct loops               │    
   │       Location: anicca-oss/runtime/mastra-graphs/                                     │    
   │                                                                                      │    
   │  L3.d action adapters       ★ Composio ★                                              │    
   │       Repo: https://github.com/ComposioHQ/composio  (250+ tool adapters)              │    
   │       Provides: Gmail send / Slack / Linear / GitHub / X / Calendar / Notion          │    
   │       Plus custom: Lancers + Coconala + Bland.ai + AgentMail (our own adapters)       │    
   │                                                                                      │    
   │  L3.e project state DB      ★ Conway state.db ★ (reuse — already has projects table)  │    
   │       ~/.automaton/state.db  schema in § 1                                              │    
   │       Both Inbox Zero (Postgres → SQLite shim) and Mastra (any KV) write here.        │    
   │                                                                                      │    
   │  L4   wallet substrate      ★ Coinbase AgentKit + viem ★ (already wired)              │    
   │       ~/.anicca-genesis/agentkit/  using ~/.automaton/wallet.json (0xa3CDd...)        │    
   │                                                                                      │    
   └──────────────────────────────────────────────────────────────────────────────────────┘    
                                                                                                
```

### § 10.3 What we still need to write (= the irreducible glue)

After forking Inbox Zero + installing Mastra + Composio, the gap is:

1. **Project-aware prompt injection** (= 100 LOC) — when Inbox Zero's rule
   engine fires, inject the project context from `projects` table into the
   LLM prompt. Inbox Zero by default treats each email standalone.

2. **Reply Zero → projects bridge** (= 50 LOC) — Inbox Zero's Reply Zero
   tracks "did they reply". We bridge that signal into the `projects.next_action_at`
   field so multi-step gigs (apply → response → followup → contract → invoice)
   become a single project row.

3. **Mastra graph per project type** (= 200 LOC) — one durable workflow per
   project archetype: `gig-application`, `github-issue`, `customer-thread`,
   `cold-outreach`. Each graph has explicit suspend-points ("wait 24h for
   reply", "wait until PR merged", "wait until invoice paid").

4. **Composio + Lancers/Coconala custom adapters** (= 150 LOC each) — the
   Japanese gig platforms aren't in Composio's 250 yet. We add them.

5. **Self-improvement edge** (= 100 LOC) — at the end of each Mastra graph
   completion, compare `actual outcome vs predicted outcome` and write a
   delta into the automaton runtime's memory store as a "learning". Next graph
   instance reads similar past graphs at the entry node.

Total ≈ **600 LOC** of glue. NOT a from-scratch system. NOT a new framework.
Fork + wire 4 mature OSS + bridge them.

### § 10.4 Why NOT pick just one

| Single-tool option | Why it fails alone |
|---|---|
| Inbox Zero only | Has Reply Zero + AI Assistant but NO multi-step project state machine. Treats each thread independently. |
| Mastra only | Has durable workflows but NO Gmail watch, NO reply tracker, NO email-specific rule engine. |
| automaton runtime only | Has the daemon loop + memory but NO Gmail-specific watcher, NO project state machine. |
| Composio only | Has adapters but NO orchestration, NO state, NO triggers. |
| n8n only | Polling-based Gmail (not push), no agent autonomy primitives, workflow editing is GUI not git-native. |
| Suna (Kortix) only | Git-as-org is interesting but no email-specific layer, requires sandbox-per-session (heavy). |

Each tool was built for a different problem. The pivot is **stop searching
for the one tool, compose the 4 that already exist correctly**.

### § 10.5 Bootstrap compute (= chicken-egg solve)

Dais 2026-06-03: *"The good thing is we're paying for its inference compute
first by authenticating with a subscription or API key."*

Bootstrap phases:

| Phase | Compute source | Anicca's USDC balance |
|---|---|---|
| 0 (now) | Dais's Anthropic Claude Max subscription + OpenAI subscription | $0 |
| 1 (week 1-2) | Same subscription, Anicca starts earning via Lancers/Coconala/x402 | $8 (SBI VC seed) |
| 2 (month 1) | Anicca buys OpenRouter API key with own USDC (Kimi K2 / DeepSeek pay-as-you-go) | self-funded |
| 3 (month 3+) | Anicca auto-top-ups OpenRouter when balance dips, Dais cancels his subscriptions | self-sufficient |

The subscription-bootstrap is **not a hack**, it's the standard chicken-egg
solve. Dais's seed is exactly what § 0 of `00-MASTER.md` calls "the original
investment" that gets repaid before independence.

---

## § 11. Verification gates (v2 additions)

| Gate | Evidence |
|---|---|
| G6 — Inbox Zero forked + running | `curl http://localhost:3000/api/health` from local Inbox Zero fork returns OK. Gmail OAuth completed. |
| G7 — Reply Zero tracking real threads | After sending a real test email and getting a reply, Inbox Zero's `replied_threads` table has 1 row with correct status. |
| G8 — Mastra graph durable across restart | Suspend a workflow at "wait 24h" step → `pm2 restart all` → workflow resumes from same step. |
| G9 — Composio Gmail send works | `composio call gmail.send_email --to=test@example.com --body=hi` returns 200. |
| G10 — End-to-end gig E2E | Real Lancers gig invitation email arrives → Anicca drafts reply (project context loaded) → judges → sends → 24h later if no reply, auto re-pings. All recorded in `projects` + `project_events`. |

---

## § 12. Changelog

| Date | Change | Author |
|---|---|---|
| 2026-06-02 | Initial draft. Encodes Dais's 2026-06-02 monologue on "Anicca treats everything as one-off". | this Claude session |
| 2026-06-03 | § 10-11 v2 PIVOT. After Dais's race call exposing v1 as naive cron design, deep-searched 30+ OSS frameworks. Adopted Inbox Zero (= the Reply Zero followup tracker I claimed didn't exist) + Mastra + Composio + Hermes 4-component stack. ≈600 LOC of glue, not a from-scratch build. | this Claude session |
