# Life Manager end-to-end handover

## Source of truth

- Spec: `/Users/anicca/anicca-project/docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`
- Remaining TODO SSOT: §10 table and its `Current cursor`
- Persisted restart goal: `/Users/anicca/anicca-project/.claude/handovers/2026-07-24_0246_life-manager-end-to-end.goal.txt`
- Verified pending count: `28`; current item: `8i REPO-CONSOLIDATE`

## Verified repository routing

- Session start/shared checkout: `/Users/anicca/anicca-project`, branch `main`, upstream `origin/main`, verified `7ce9db9b3a4ebdf3a9a262eea9f59f4213f0e9ac`. It has 16 pre-existing untracked paths. Read/fetch only; do not edit, switch, stage, clean, merge, or rebase it.
- Spec/handover writes: `/Users/anicca/anicca-project/.worktrees/lm-8i-handover-20260724`, branch `docs/lm-8i-handover-20260724`, base `7ce9db9b3a4ebdf3a9a262eea9f59f4213f0e9ac`, push target `origin/docs/lm-8i-handover-20260724`.
- Canonical implementation: `/Users/anicca/anicca/.worktrees/one-repo-migration`, branch `feat/one-repo-migration`, HEAD `bfbcb915cbf7ed08da2d44c498bd82b9a5f07ae4`, clean, no unique commits, nine behind verified canonical `origin/main=303fc30a50e4db88522d88c6da71b40bf2e67665`. Fetch and fast-forward only before editing; push target `origin/feat/one-repo-migration`.
- Protected checkout: `/Users/anicca/anicca`, branch `feature/dist1-mcp-launchd`, HEAD/upstream `72b74d59df80cb72936ccd04f5ee1ed7a19e7ec0`, 17 modified live log files. Do not touch it.
- Reviewers use temporary detached snapshots of exact candidate commits and never edit writable worktrees.

## Verified state

- `Daisuke134/life-manager` is repository ID `1248111245`, but its main has `apps/life-manager=0`, `packages/engine=0`, and the canonical consolidation spec=0.
- `Daisuke134/anicca-products` still contains `apps/life-call` and the spec. Rename is done; whole-product consolidation is not.
- PRs `#355` and `#356` are merged; they add `8i`, set pending count to 28, route `9b` after `8i`, and require VPS/cloud browser execution.
- Latest successful Life Call production deployment is `b3fd36f5-2f8e-4b54-b714-d387e7eb194c` at commit `4836ca90ddd4999fc952718023cf92583220ca2c`; later documentation commits are Railway `SKIPPED`.
- Fresh read-only smoke: production `/health` is HTTP 200 with `ok=true`, and `/panel` is HTTP 200 with `cache-control: no-store`.
- No product/provider/account mutation was performed by the handover run. No in-thread worker remains active.

## Active blockers

- `8e`: code/release pass; production L3 requires a real controlled target-inbox Message-ID readback.
- `8f`: code/schema/release pass; production L3 requires a real location input that reaches the Bot API webhook. Do not run a fourth MTProto simulation.
- These blockers do not permit stopping independent work. Phase 1 cannot be called done while either remains pending.

## First safe resume action

From the shared local `main`, run a fresh fetch and verify HEAD/upstream/dirty state without editing. Read this handover and spec §10 from current `origin/main`. Then inspect both routed worktrees, require them clean, fast-forward the spec worktree to current `anicca-products/origin/main` and the implementation worktree to current `life-manager/origin/main`, create durable `execution-notes.md`, and execute `8i` through Superpowers/TDD/review/real L3. Continue through all remaining rows; do not stop after planning or one phase.
