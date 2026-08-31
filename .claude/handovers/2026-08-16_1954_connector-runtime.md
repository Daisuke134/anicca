# Connector runtime handover

> **SUPERSEDED:** Do not resume from this handover. Use `.claude/handovers/2026-08-16_2040_connector-core-recovery.md`; the product contract and Active TODO were narrowed by PR #2801.

## Canonical state

- Repo: `/Users/operator/Projects/mr-bot-main`
- Audit/spec worktree: `/Users/operator/Projects/mr-bot-main/.worktrees/connector-status-20260816`
- Branch: `docs/connector-status-20260816`
- Audited base: `5a9f390b2eca09643697f90d45ac9ac7507fc0a4`
- Reconciled spec commit: `204044ed16b68df394fa0f8f8fdf4d97a870a36b`
- SSOT: `docs/superpowers/specs/2026-08-01-dais-mr-bot-five-phase-execution-spec.md`
- Current ordered work: section `0.2.1 Active remaining TODO SSOT`
- Ideal architecture: section `0.2.2 Connector ideal loop — start to finish`

Do not edit the shared main checkout or either dirty healer worktree. Fetch first, then create a fresh implementation worktree from current `origin/main` after confirming it contains the reconciled `0.2.1` section.

## Verified current state

- Latest real success is wake `wake-d7fc192bd446f613acd15b02`: `applied_bundle / peatix / registered`, failure count 0.
- Bundle `bcb664…` contains provider receipt, PNG SHA `63c12c…`, Google Calendar ID/readback, Telegram message `20545`, photo `20546`; wake delivery is `20549`.
- Durable totals: bundles 14, checkpoints 33, wake reports 140, deliveries 152, actions 1807.
- Connector regression suite passes `560/560` when the isolated worktree resolves the existing `playwright-core` and `jsqr` dependencies from the main checkout.
- Native label is loaded with the intended main `run.sh` and 09:00 schedule, but has `runs 0 / never exited` since reload. The latest wake is foreground evidence, not scheduled-owner evidence.
- Broken legacy healthcheck and healer labels remain loaded with `EX_CONFIG` and deleted-worktree paths. Retired host bridge remains loaded/running on `18793`.
- Connector-required browser `127.0.0.1:9222` has no listener. Gig-owned `:9223` is healthy and must not be touched.
- TECH PLAY has one real Calendar-safe selected candidate but stopped at `techplay_direct_requires_harness`; it is an implementation/live-acceptance item, not merely an external wait.

## Resume order

1. `C-OPS-01`: retire only the three stale legacy labels and prove native is the sole scheduler owner.
2. `C-OPS-02`: restore a durable Connector browser owner on `:9222` without touching Gig `:9223`.
3. `C-OPS-03`: run exactly one supervised native launchd wake and prove launchctl run-count increment, terminal wake, cleanup, and receipt chain.
4. `C-LIVE-01`: repair/complete TECH PLAY through its bounded harness and obtain the first real `applied_bundle`.
5. `C-LIVE-02`–`05`: obtain first live bundles only when exact Calendar-safe candidates/auth exist; keep external waits truthful.
6. `C-DUR-01`: prove the next natural 09:00 or login-recovery run end to end.

## First safe action

Read the SSOT, fetch current refs, and repeat the read-only label/port/process/lock/state audit. Before any production unload/restart, show the exact labels/PIDs/ports and the rollback path required by the production-service safety rule. Never kill shared browser or OS foundation services.

## Required execution discipline

Sol owns the spec, plan, acceptance criteria, production E2E, final status, commit/push, and Telegram reporting. For each one-item slice, delegate only production/test implementation to Luna; Luna must not edit/reinterpret the spec. After implementation, use a fresh read-only Sol adversarial verifier, then return fixes to the same Luna. Do not claim completion from unit tests or foreground execution alone.

## Durable artifacts and side effects

- Spec commit above is pushed to `origin/docs/connector-status-20260816`.
- No production state was changed during this audit.
- This handover's exact continuation goal is in `2026-08-16_1954_connector-runtime_goal.txt`.
