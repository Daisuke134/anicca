# Handover: macOS Mr.bot Loop Control Plane

Spec/TODO SSOT: `/Users/anicca/Projects/mr-bot-main/.worktrees/codex-account-failover/docs/superpowers/specs/2026-08-27-macos-loop-control-plane-design.md`, section `6. Execution Steps and Ordered TODO`.

Writable route: `/Users/anicca/Projects/mr-bot-main/.worktrees/codex-account-failover`, branch `codex-account-failover`, upstream `origin/codex-account-failover`, verified commit `80d30c19da8100b9c8df202d12f5747d5a730f17`. Remote `main` was the same commit. Do not edit or switch the dirty shared checkout `/Users/anicca/Projects/mr-bot-main`.

Completed: dedicated macOS-only control-plane spec, visual architecture, acceptance criteria, test matrix, and 12 ordered TODOs were committed and pushed. Existing `config/loop-registry.json` is chosen as the single future registry; implementation has not started. CFO and Writer launchd plists read back `CODEX_HOME=/Users/anicca/.codex-acct2`. Runtime pointers at handover time: `~/loops/current` -> release `2eff890d`; `~/gig/releases/mr-bot/current` -> `80d30c19d`.

Current item: TODO 1 only — inventory every installed Mr.bot-owned `ai.anicca.*` launchd label and classify owner/domain/effect/state/release. Do not start TODO 2 until TODO 1 evidence and spec state are committed.

Active blocker to re-read, not assume: Fundraiser was loaded/running but its prior terminal was `EX_TEMPFAIL 75` from disk pressure; free space was about 1.0 GiB. Check current launchd, disk, immutable release, and official loop evidence before reporting status.

Boundaries: proceed serially, one TODO at a time; no subagents; update the spec as facts change; preserve credentials, receipts, ledgers, protected sessions, active releases, and external-effect dedupe. Do not implement multi-subscription quota circumvention. Profile isolation and explicit routing are allowed; uninterrupted capacity must use provider-supported API capacity.

First safe action: `git fetch origin`, verify HEAD/upstream/dirty state, read the spec completely, then perform read-only TODO 1 inventory using installed plist files plus `launchctl print`/`print-disabled`; write the coverage evidence and update only TODO 1 state.

Exact user-sendable goal is stored beside this file in `2026-08-27_2326_macos-loop-control-plane-goal.txt`.
