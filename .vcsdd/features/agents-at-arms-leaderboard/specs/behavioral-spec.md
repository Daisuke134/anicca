# Behavioral Spec — agents-at-arms-leaderboard (VCSDD Phase 1a/1b, lean)

Source design: `docs/superpowers/specs/2026-07-01-agents-at-arms-live-leaderboard-design.md`.
Scope of THIS feature slice = the **data contract + rendering** of the public leaderboard
(`dashboard-sync` emits a ranked `agents[]`, the UI renders it with a `#agent-hackathon` filter).
Out of scope here (separate sprints/tasks #7,#9): Supabase migration, spawn-time registration.

## 1a. Behavioral requirements (EARS)

- **R1** WHEN `dashboard-sync` aggregates instance rows, the system SHALL emit a top-level `agents`
  array where each element has `{instance_id, handle, funding_type, model_current, net_worth_usd,
  revenue_today_usd, revenue_mtd_usd, revenue_by_source, status, tags, last_heartbeat}`.
- **R2** The `agents` array SHALL be sorted descending by `net_worth_usd` (the default rank), ties
  broken by `revenue_mtd_usd` descending.
- **R3** WHERE a money field (`net_worth_usd`, `revenue_today_usd`, `revenue_mtd_usd`) is not available
  from an on-chain source, the system SHALL omit that field (leave undefined) rather than emit `0` or
  a self-reported value (no-fake invariant, useDashboard §v2.7/§v2.10).
- **R4** WHEN an instance's `last_heartbeat` is older than the staleness window (default 10 min), the
  emitted `status` SHALL be `idle` regardless of the stored status.
- **R5** WHEN the dashboard UI renders, it SHALL display a leaderboard row per agent in `agents[]`
  order, showing rank, handle, `model_current`, `net_worth_usd`, `revenue_today_usd`,
  `revenue_mtd_usd`, and `status`.
- **R6** The UI SHALL provide filter controls `All | #agent-hackathon | Ours`; selecting
  `#agent-hackathon` SHALL show only agents whose `tags` include `agent-hackathon`; `Ours` SHALL show
  only agents whose `funding_type` is not a hackathon entrant (our own instances); `All` SHALL show
  every agent.
- **R7** WHERE a money field is undefined for an agent, the UI SHALL render a neutral placeholder
  (e.g. `—`), never `$0`.
- **R8** WHEN the filtered set is empty, the UI SHALL render an explicit empty state, not a blank area.

## 1b. Verification architecture (how each requirement is proven)

| Req | Test kind | Proof |
|---|---|---|
| R1 | unit (telemetry-aggregate) | given fixture rows → output has `agents[]` with exact shape |
| R2 | unit | unsorted fixture → output order strictly by net_worth desc, mtd tiebreak |
| R3 | unit | row missing on-chain money → field absent (assert `!== 0`, `=== undefined`) |
| R4 | unit | row with stale `last_heartbeat` → `status === 'idle'` |
| R5 | component test + **browser E2E** | render fixture `agents[]` → rows present in order; CloakBrowser screenshot |
| R6 | component test + **browser E2E** | click `#agent-hackathon` → only tagged rows; click `Ours` → only ours |
| R7 | component test | agent w/ undefined money → DOM shows `—`, not `$0` |
| R8 | component test | empty filtered set → empty-state node present |

## Invariants (carry into impl, never violate)
- **INV-NOFAKE**: money shown on the board is on-chain-derived or omitted; never a self-reported or
  fabricated number. (Ranks by real net worth only.)
- **INV-OWN-STATE**: agents write only their own row; the UI/sync never writes agent state.

## Definition of done (this slice)
- All R1–R8 tests green (unit + component).
- Adversary (fresh context, disk-only) PASS on spec + impl.
- **My own browser E2E** on the rendered leaderboard (CloakBrowser): leaderboard renders a ranked
  list from real `/dashboard.json`, the `#agent-hackathon` filter works, money shows real values or
  `—` (never fake `$0`). Full-page screenshot captured.
