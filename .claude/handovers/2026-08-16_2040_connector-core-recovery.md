# Connector core recovery handover

## Canonical state

- Spec: `/Users/operator/Projects/mr-bot-main/docs/superpowers/specs/2026-08-01-dais-mr-bot-five-phase-execution-spec.md`
- Product contract: `0.1.1 Connector current product contract`
- Remaining-TODO SSOT: `0.2.1 Active remaining TODO SSOT`
- Ideal flow: `0.2.2 Connector ideal loop — start to finish`
- Canonical repo/branch/commit: `/Users/operator/Projects/mr-bot-main`, `main`, `f32eee4d2392a63597b3505a49b2bf50fdb1145d`
- Handover worktree/branch: `/Users/operator/Projects/mr-bot-main/.worktrees/connector-core-handover-20260816`, `docs/connector-core-handover-20260816`

The shared main checkout and existing healer worktrees may contain work owned by other sessions. Do not edit, switch, reset, clean, or delete them. Create the implementation worktree named by the goal after a fresh fetch.

## Verified resume state

- Current item is `C-CORE-01`; execute `C-CORE-01` through `C-CORE-07` in SSOT order.
- Product scope is narrow: Luma then Connpass are primary; existing remaining providers are fallback and their additional first-live proofs are non-blocking. AI/crypto is a soft preference and never an exclusion rule.
- Connector writes only the event itself to Google Calendar. It does not calculate/write travel time, buffers, routes, or Mr.bot Web App enrichment.
- Current code still requires `createConnectorRouteMinutes`/`homeLocation`/`routeMinutes` in native candidate gating; remove that drift in `C-CORE-03` with a regression proving no route dependency.
- Runtime readback at handover: native label loaded, not running, runs 0, never exited; healthcheck runs 82 and healer runs 5, both `EX_CONFIG`; retired host bridge is running on `127.0.0.1:18793`; Connector `:9222` has no listener; Gig-owned Chromium `:9223` is listening and must not be touched.
- Latest durable wake remains `wake-d7fc192bd446f613acd15b02`, `applied_bundle`, failure count 0. Latest verified bundle is Peatix `bcb664…`, registered, Telegram message `20545`, photo `20546`.
- Connector suite was verified `560/560 PASS` before PR #2801 merged. Spec contract/fence/diff checks passed. These static checks do not replace production E2E.
- No production state was changed while creating this handover.

## First safe resume action

Fetch `origin/main`; confirm it contains merge `f32eee4d2` and the seven C-CORE rows; create the isolated implementation worktree/branch from current `origin/main`; then repeat the read-only label/plist/port/process/lock/latest-wake audit. Before unloading or restarting anything, resolve the exact targets and preserve Gig `:9223`, unrelated browser profiles/tabs, plists, and durable state.

## Live/public side effects

- Product-contract correction is merged by PR `#2801` at `f32eee4d2`.
- Existing Calendar/Telegram/provider receipts are historical evidence only; do not generate a duplicate application to manufacture proof.
- Exact continuation goal: `.claude/handovers/2026-08-16_2040_connector-core-recovery_goal.txt`.

