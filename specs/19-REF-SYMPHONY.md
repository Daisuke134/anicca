# 19 — REF: openai/symphony (the Issue→autonomous-run→proof engine)

| Field | Value |
|---|---|
| Repo | github.com/openai/symphony · Elixir reference impl + language-agnostic `SPEC.md` (RFC-2119) · 30MB · pushed 2026-06-01 |
| Read at | SOURCE: `SPEC.md` (the canonical normative spec OpenAI published for re-implementation) |
| Role for Anicca | THE engine for spec 18 §1/§2: anicca-oss GitHub Issues → per-issue isolated run → proof → handoff/close |

> Read the ACTUAL `SPEC.md` (not the README). This file documents what symphony ACTUALLY specifies,
> verbatim-grounded, then how Anicca adopts it. No interpretation-as-fact.

## § 1. What symphony ACTUALLY is (from SPEC.md §1-3)
A **long-running daemon** that: continuously reads work from an issue tracker (Linear in v1) → creates
an **isolated per-issue workspace** → runs a **coding-agent session** for that issue inside it →
policy lives in an in-repo **`WORKFLOW.md`** (YAML front-matter + prompt body) → bounded concurrency,
retries, reconciliation → a run ends at a **workflow-defined handoff state** (e.g. `Human Review`),
not necessarily `Done`.

Explicit boundary (SPEC §1): "Symphony is a scheduler/runner and tracker READER. Ticket writes (state
transitions, comments, PR links) are performed BY THE CODING AGENT using its tools." → the orchestrator
schedules; the agent does the work + updates the ticket.

## § 2. The 8 components (SPEC §3.1) + 6 layers (§3.2)
```
 components:                                    layers (port boundaries):
  1 Workflow Loader  reads WORKFLOW.md →          1 Policy        WORKFLOW.md prompt + team rules (in-repo)
                     {config, prompt_template}    2 Configuration typed getters, defaults, env indirection
  2 Config Layer     typed getters + validation   3 Coordination  orchestrator: poll, eligibility, concurrency,
  3 Issue Tracker    fetch candidates / states /                  retries, reconciliation
                     terminal (reconcile+cleanup) 4 Execution     workspace lifecycle + agent subprocess protocol
  4 Orchestrator ★   owns poll-tick + in-mem      5 Integration   tracker adapter (Linear) — swap per tracker
                     state; dispatch/retry/stop   6 Observability structured logs + OPTIONAL status surface
  5 Workspace Mgr    issue→path, mkdir, hooks,
                     cleanup terminal issues
  6 Agent Runner     mkworkspace → build prompt(issue+template) → launch coding-agent app-server → stream updates
  7 Status Surface   OPTIONAL operator view
  8 Logging          structured sinks
```

## § 3. Domain model (SPEC §4.1, verbatim fields)
```
 Issue:        id · identifier(ABC-123) · title · description · priority(lower=higher) · state ·
               branch_name · url · labels(lowercased) · blocked_by[{id,identifier,state}] · created/updated_at
 WorkflowDef:  config(YAML front matter) + prompt_template(MD body, trimmed)
 ServiceConfig:poll interval · workspace root · active/terminal states · concurrency limits ·
               agent exec/args/timeouts · workspace hooks
 Workspace:    path(abs) · workspace_key(sanitized id) · created_now(gates after_create hook)
 RunAttempt:   issue_id · identifier · attempt(null=first,>=1 retry) · workspace_path · started_at · status · error
 LiveSession:  agent-subprocess metadata while running
```

## § 4. Operational guarantees (SPEC §2.1 goals)
- poll on fixed cadence + dispatch with **bounded concurrency**
- single authoritative orchestrator state; **exponential backoff** on transient failure
- **deterministic per-issue workspaces**, preserved across runs
- **stop** active runs when issue state changes make them ineligible
- restart recovery from tracker/filesystem WITHOUT a persistent DB (in-mem scheduler state not restored)
- NON-goals: no web UI, no general workflow engine, no built-in ticket-edit logic (that's the agent + WORKFLOW.md)

## § 5. HOW ANICCA USES IT (the adoption, not interpretation)
```
 symphony concept     →  Anicca instantiation
 ─────────────────────────────────────────────────────────────────────────────
 issue tracker(Linear)→  GitHub Issues on github.com/Daisuke134/anicca-oss (Integration adapter swapped)
 coding-agent         →  a Hermes-Anicca session (run_agent.py) spawned per issue
 WORKFLOW.md (policy) →  anicca-oss/WORKFLOW.md = Anicca's per-issue prompt + constitution + DoD + eval-gate
 per-issue workspace  →  a Daytona sandbox (or local dir) per issue — isolated
 orchestrator poll    →  Hermes cron ticks → reads open issues → dispatches (bounded concurrency)
 proof-of-work        →  tests + eval-loop score(≥0.7) + PR → agent updates the issue + opens PR
 handoff state        →  "Human Review" (Dais) OR auto-close when eval+CI pass (no human)
 ADOPTION: port SPEC.md's 6 layers; reuse the Elixir ref OR re-implement the Coordination+Execution
           layers as a Hermes skill (forum-issues skill, spec 18 task #334). symphony's SPEC.md is
           explicitly "implement in a language of your choice" — we implement the orchestrator in
           Hermes/Python and keep WORKFLOW.md in anicca-oss.
```

## § 6. ASCII — symphony engine driving the Anicca forum
```
  anicca-oss GitHub Issues ──poll(cron)──► ORCHESTRATOR (Hermes) ──dispatch (concurrency cap)──┐
     ▲  (agent writes back: comment, PR link, close)                                          │
     │                                                                                        ▼
     │                                              per-issue WORKSPACE (Daytona sandbox, isolated)
     │                                                         │  build prompt = issue + WORKFLOW.md
     │                                                         ▼
     │                                              Hermes-Anicca session runs the work
     │                                                         │  proof: tests + eval≥0.7 + PR
     └─────────────────────────────────────────────────────────┘  → handoff(Human Review) OR auto-close
  reconciliation: issue state changed → stop ineligible runs · retries w/ exp backoff · terminal → clean workspace
```

## § 7. Changelog
| 2026-06-04 | Read SPEC.md at source. symphony = issue→isolated-workspace→agent→proof→handoff daemon (6 layers, bounded concurrency, reconciliation, WORKFLOW.md policy). Adoption: Linear→GitHub Issues, coding-agent→Hermes-Anicca, implement orchestrator as the forum-issues skill (spec 18 #334). |
