# 23 — REF: desplega-ai/agent-swarm (Lead→worker→shared-memory : THE full integration blueprint)

| Field | Value |
|---|---|
| Repo | github.com/desplega-ai/agent-swarm · TypeScript/Node · 155MB(gh-api read, no clone) · "evolves every single day" |
| Read at | SOURCE: README architecture + src/ tree + src/be/memory/index.ts + src/github/task-reactions.ts + src/commands/worker.ts |
| Role for Anicca | THE closest end-to-end reference for spec 18: Lead receives tasks (GitHub/email/Slack/API) → delegates to isolated workers → workers write learnings to a SHARED MEMORY → swarm compounds. = forum + self-improve + swarm + collective brain in ONE running system. |

> Read the ACTUAL source (README architecture + src/ tree + 3 core files). Documented from code, adoption stated separately.

## § 1. What agent-swarm ACTUALLY is (from README + source)
"Your Company's Compounding Intelligence Layer. A system of AI agents that **remember, reason, act and
get better with every task**." A **lead agent** receives tasks (from Slack/GitHub/GitLab/Linear/Jira/
email/API) → breaks them down → delegates to **worker agents running in isolated Docker** → workers
execute, ship, and **write their learnings back to a shared memory so the whole swarm gets smarter
every session**. Lead coordinates; workers share learnings horizontally. "AI Native", not "AI First".

README architecture (verbatim shape):
```
   IN ──► LEAD(SOUL, CLAUDE.md) ──► WORKERS[ Worker·Worker·Worker ] (in Docker)
                                       │ reads context   │ writes learnings
                                       └──────► BRAIN ◄──┘
                                       └──► OUT
```

## § 2. The real mechanisms (file:line / dir grounded)
```
 INTAKE (lead receives work from many sources):
   src/github/task-reactions.ts  addEyesReactionOnTaskStart(task) [:18] — when a task →in_progress,
     adds 👀 reaction on the source GitHub issue_comment / PR review [:10-30]. task.source==="github",
     task.vcsRepo, task.vcsEventType ("issue_comment" | "pull_request_review" | ...). → GitHub Issues/PRs
     ARE the task feed, and the agent reacts on the originating comment (visible progress on the issue).
   src/gitlab/ · src/agentmail/{app,handlers,templates,types}.ts — GitLab + EMAIL intake (email → task).
   src/http/{agents,active-sessions,core}.ts — HTTP API intake + live session view.
   src/heartbeat/index.ts — heartbeat loop (liveness / scheduling).

 EXECUTION (lead → worker):
   src/commands/worker.ts  runWorker(opts)=runAgent(workerConfig) [:13]; workerConfig {role:"worker",
     defaultPrompt:"/start-worker", metadataType:"worker_metadata"} [:6-11]. Workers run in isolated
     Docker (README). src/commands/{codex-session-runner,resume-session}.ts — session run + resume.

 SHARED MEMORY (the compounding brain):
   src/be/memory/index.ts  getMemoryStore()→SqliteMemoryStore [:19]; getEmbeddingProvider()→
     OpenAIEmbeddingProvider [:10] (semantic memory = embeddings + SQLite store).
   src/be/memory/raters/registry.ts — RATERS registry: learnings are RATED (quality scoring of what
     gets written to the brain). src/be/seed/registry.ts + src/be/seed-skills/ + src/be/seed-scripts/
     catalog/{task-context-gathering,task-failure-audit}.ts — seeded skills + a FAILURE-AUDIT task
     (learn from failures) + a CONTEXT-GATHERING task. src/be/swarm-config-guard.ts — config guard.
```

## § 3. HOW ANICCA USES IT (adoption, not interpretation)
```
 agent-swarm piece               →  Anicca instantiation (spec 18)
 ────────────────────────────────────────────────────────────────────────────────────────
 GitHub task-reactions (👀)      →  the FORUM (spec 18 §2 / spec 19 symphony): anicca-oss Issues =
   intake + visible progress        task feed; Anicca reacts/comments on the issue as it works.
 agentmail intake (email→task)   →  "email Anicca → it files an issue" (spec 18 §1 step 3 inbound:
                                     Dais emails → Anicca opens an issue). AgentMail already provisioned
                                     (anicca-genesis@agentmail.to) — wire it as an intake adapter.
 GitLab / HTTP / API intake      →  multi-source intake adapters (same pattern symphony §5 swaps).
 lead → worker (isolated Docker) →  lead Anicca delegates to worker Anicca in isolated workspace
                                     (Daytona sandbox = our "Docker"; swarms HierarchicalSwarm = topology).
 SHARED MEMORY (SQLite+embeds)   →  the COLLECTIVE BRAIN: per-instance learnings → shared, semantic
   + raters/registry (rated)        memory; the rater = our EVAL-LOOP gate (spec 16 §C) deciding what
                                     learning is good enough to write + roll out to all (spec 18 §2).
 seed-scripts/task-failure-audit →  the self-improve loop's "learn from failure" step (spec 18 §1):
   + task-context-gathering         a failed run → audit task → learning written to brain.
 heartbeat + resume-session       →  liveness + restart recovery (pairs with sutando registry, spec 22).
 ADOPTION: agent-swarm is the REFERENCE ARCHITECTURE for the whole spec 18 system (intake → lead →
   isolated worker → shared rated memory → compound). We do NOT run its TS stack; we re-implement the
   same shape on the automaton runtime: symphony (spec 19) = the orchestrator/intake, swarms (spec 21) = the lead→worker
   topology, the shared brain = our memory + eval-rater, MiroFish (spec 20) = predict, sutando (spec 22)
   = resurrection. agent-swarm proves the END-TO-END loop runs as a real product — it de-risks spec 18.
```

## § 4. ASCII — agent-swarm shape mapped onto Anicca
```
  INTAKE adapters                LEAD ANICCA              WORKERS (isolated: Daytona sandbox)
  ┌ GitHub Issues (forum) ─┐                          ┌ worker Anicca: earn gig
  ├ AgentMail (email→issue)├──►  reads + breaks down ──┼ worker Anicca: x402 server
  ├ GitLab / HTTP / API    ┘     delegates (swarms     └ worker Anicca: research
  │                               HierarchicalSwarm)          │ each ships + writes learning
  │  reacts 👀 on the issue                                   ▼
  │  (visible progress)                          SHARED BRAIN (semantic memory + RATER/eval-gate)
  └────────────◄── learning rated ≥0.7 → rolled out to ALL instances (spec 18 §2) ──────────┘
  failure → task-failure-audit → learning ;  heartbeat + resume-session → liveness/recovery
```

## § 5. Changelog
| 2026-06-04 | Read source (README Lead→worker(Docker)→shared-brain compounding; github/task-reactions 👀 on issue; agentmail email-intake; commands/worker runAgent; be/memory SQLite+OpenAI-embeds + raters/registry rated learnings; seed-scripts task-failure-audit + context-gathering; heartbeat; resume-session). Adoption: agent-swarm = the END-TO-END reference architecture for spec 18 (intake→lead→isolated worker→shared rated memory→compound+rollout); re-implemented on the automaton runtime via symphony(19)+swarms(21)+memory/eval-rater+MiroFish(20)+sutando(22). De-risks spec 18 by proving the loop runs as a real product. |
