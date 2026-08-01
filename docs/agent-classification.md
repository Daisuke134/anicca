# Life Manager agent classification

This audit applies the five criteria in the [Agent Registry design](superpowers/specs/2026-08-01-life-manager-agent-registry-design.md): model reads state, chooses an action/tool, observes a result, can revise the next action, and produces verifiable evidence for effects.

## Accepted agent roles

| Agent | Classification | Why |
|---|---|---|
| Life Manager Orchestrator | `live` | `runtime/loop` is an explicit ReAct wake loop with a pluggable model brain, tool selection, execution, ledger persistence, and later wakes that observe prior results. |
| Gig Work Agent | `legacy_live` | A persistent model session and bounded subcalls judge feasibility, operate marketplace/browser tools, verify the real surface, and learn from outcomes. |
| Writer Agent | `legacy_live` | The 13-row writer family and article spec define research, drafting, adversarial revision, publishing, measurement, and self-improvement. The implementation still lives behind legacy commands, so it is not `live`. |
| Capafy Agent | `legacy_live` | The model reads sales/state, chooses the highest-value marketplace action, drives tools, verifies remote status, and invokes self-repair from failures. |
| Solana Trading Agent | `live` | The registered slot delegates research, sizing, trade/wait judgment, execution, and traces to the wallet-bound Franklin agent while deterministic gates cap spend. |
| Polymarket Agent | `live` | Model consensus and market signals choose market, side, and size; wrappers enforce kill switches and record independently verifiable positions and cycles. |
| Marketing Agent | `legacy_live` | Product manifests feed a shared model runner that chooses copy/content actions, publishes, reads metrics, and revises later passes; canonical adapters exist but legacy jobs still own much of execution. |
| Clip / Affiliate Agent | `legacy_live` | A persistent model loop observes metrics and lessons, decides account/content actions, publishes, verifies reach, and self-heals. Deterministic producer/poster components remain tools. |
| Development Agent | `live` | The canonical D0 loop gives one issue to a fresh coding model, requires TDD and independent gates, and produces a PR/receipt rather than claiming success from model output. |
| Job Application Agent | `shadow` | The portable app invokes the canonical model runner for daily and inbox passes, with ATS, Gmail, calendar, schemas, and evidence. Real end-to-end application receipts are still an explicit completion gate. |
| CFO, Health, Mobile, Event, Fundraising roles | `planned` | The product organization and boundaries are specified, but no complete model-directed specialist loop with the required evidence exists yet. Existing deterministic modules/adapters are tools for these future agents. |

## Useful things that are not agents

| Component | Classification | Reason |
|---|---|---|
| `skills/registry.json` | capability catalog | Its 22 slots are tools/actions exposed to an agent, not 22 independent decision-makers. |
| `loop-adapters.json` | runtime adapter registry | Its six adapters normalize execution and effects; they do not own goals or model judgment. |
| 399-row runtime inventory | scheduler/job inventory | Rows include cron, launchd, workers, monitoring, external services, and legacy loops. Runtime families are referenced by one agent role instead of being copied as agents. |
| `report` / financial report | deterministic reporting job | Formats and sends known data; no observe-decide-act loop. |
| `x402_sell` | service capability | Serves a preset catalog and records sales; the calling agent decides strategy. |
| `yield` | financial tool | Executes a bounded capital action; the calling agent decides whether and when to use it. |
| `economy/ubi` | policy/bookkeeping tool | Computes and logs a fail-closed gate; transfers are separately controlled. |
| `economy/lending` | deterministic bookkeeping | The registry itself states that eligibility, sizing, and servicing use zero model judgment. |
| `earn/taskmarket` | deterministic work executor | Current selection is fixed code and one image-generation call; there is no result-driven model strategy loop. |
| `earn/clip-producer` | deterministic media worker | Produces and verifies media selected by a parent agent. |
| `self/spawn` / `self/spawn-child` | capability and deployment tool | A parent model may choose them, but eligibility and deployment gates are deterministic. |
| healthchecks, watchdogs, backups, tunnels | infrastructure | They keep systems available and must not be presented as autonomous roles. |

## Inventory relationship

```text
one agent role
    └── zero or more capabilities
    └── zero or more canonical adapters
    └── zero or more legacy runtime families
            └── many concrete jobs
```

For example, the user sees one Writer Agent. Engineers can follow its `writer-loop` reference to the 13 captured legacy jobs without describing 13 schedulers as 13 agents.
