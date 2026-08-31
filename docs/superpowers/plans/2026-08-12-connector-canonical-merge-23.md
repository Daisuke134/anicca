# Connector Item 23 — canonical merge and post-merge wake

## Goal

Merge the reviewed Connector completion branch into canonical `main` without touching the dirty canonical checkout, move the single production LaunchAgent to the merged commit, and accept the next official wake only from durable readback evidence.

## Ponytail full gate and size

- Reuse Git's three-way merge in one clean worktree. Do not copy the repository, rewrite history, force-push, create a second scheduler, or delete the user's dirty main checkout.
- `git merge-tree` reports four conflicts out of 284 changed files: one Telegram test, the native write pipeline and test, and one historical plan. Conflict resolution is exact four files; production conflict scope is one existing file and about 10 conflicting lines, not a Connector redesign.
- Preserve all auto-merged canonical late-approval/CFO work. For the four conflicts, the feature side is the newer accepted Connector contract: registration PNG/photo binding, provider-neutral inventory, Luma confirmation/ticket evidence, and their accumulated tests. Resolve to that feature content, then prove that both canonical and Connector tests still pass. Do not weaken a failing assertion to make the merge green.

## Goal → Loop → Verify → State

1. Create `/Users/operator/Projects/mr-bot-main/.worktrees/connector-canonical-integration` on a new integration branch at fresh `origin/main`. Merge `origin/feature/connector-native-completion` with a merge commit.
2. Luna owns only the four conflicted files. It resolves the three code/test files and historical plan to the feature-side accepted content, stages them, and runs the focused native write/Telegram tests. It must not alter any other auto-merged file.
3. Sol verifies zero unmerged paths, full Connector restart/evidence/runner/native/entrypoint regressions, the canonical late-approval tests touched by upstream, syntax, `git diff --check`, secret scan, and a fresh read-only Sol review. Commit the merge and push integration branch.
4. Open a PR from the integration branch to `main`, verify required checks, and merge non-force. Confirm `origin/main` contains both prior canonical HEAD and feature HEAD. Keep the user's existing dirty main checkout untouched.
5. Production-state change: render/install the one mode-0600 native plist with program and working directory pointing to the clean integration worktree at the exact merged `origin/main` commit. Bootout/bootstrap only the existing native label; do not load healthcheck, healer, bridge, fill-gaps, or daily-report.
6. Kickstart the existing native label exactly once without `-k`. Accept an `applied_bundle` or an idempotent continuation/safe bounded circuit only when the durable wake report has a positive Telegram provider ID, applied-bundle/checkpoint counts do not duplicate, process/lock/owned page clean up, the four unrelated CDP pages remain, and launchd exit matches the terminal contract.
7. Update README/SSOT Item 23 with merge SHA, production path, wake ID, report/delivery deltas, bundle/checkpoint deltas, provider audits, and remaining external-condition Item 19 rows. Commit and push the final docs to `main` through the same clean integration path.

## Failure boundaries

- Any unexpected conflict, failing canonical test, missing remote ancestry, or dirty integration worktree stops before production cutover.
- Any post-merge wake with unknown effect, missing positive Telegram receipt, duplicate bundle/checkpoint/delivery, leaked owned page, or stale lock keeps Item 23 open and triggers a new minimal repair slice; do not change provider order, circuit threshold, or safety gates for acceptance.
- Item 19 providers with current Calendar-free/eligible count zero remain visible external-condition TODOs. Item 23 does not fabricate an application to close them.
