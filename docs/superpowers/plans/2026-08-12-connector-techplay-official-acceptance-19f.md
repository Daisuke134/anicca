# TECH PLAY Official Launchd Acceptance Plan

**Goal:** Use the existing launchd owner to prove either a real TECH PLAY bundle or a truthful healthy no-effect result through discovery, Calendar gating, Telegram, and owned-page cleanup.

## Preflight evidence

- Initial branch/worktree was clean and pushed through SSOT commit `2077c3519`; the final verified repair is code commit `96277e017`.
- `gui/501/ai.anicca.mr-bot-connector-native` is loaded, points to this exact worktree, is not running, has no owner lock, and has a single daily `09:00` trigger.
- Contrary to the older chat statement, the production schedule is currently loaded; this plan records the measured state instead of preserving that contradiction.
- Shared CDP `127.0.0.1:9222` has exactly four pre-existing page targets; all must survive unchanged.
- Prior durable result is `completed_no_effect / provider_discovery_failed / consecutive_failure_count=2`; prior logs are historical and do not prove the current build.

## Acceptance contract

- [x] Announce and execute one `launchctl kickstart gui/501/ai.anicca.mr-bot-connector-native` without `-k`, plist reinstall, or manual executor. After the measured exit-contract failure, unload, repair, reload, and execute one sequential verification wake; concurrent owners remain zero.
- [x] Observe bounded termination, no concurrent owner, and no stale lock for both wakes.
- [ ] A successful TECH PLAY acceptance requires `applied_bundle`, provider `techplay`, provider status `registered`, one final action, one Calendar event with exact canonical URL, valid receipt/PNG, Telegram message/photo receipts, and bundle/checkpoint readback.
- [x] Preserve all four pre-existing page targets and close only the connector-owned page.
- [x] The wake completed without a non-conflicting TECH PLAY candidate and reported the exact provider outcome without claiming application success.
- [x] The first wake exposed a process-exit failure; unload the daily schedule before repair/retry so no unattended mutation could occur.
- [x] Independently re-read bundle/Calendar write counts, Telegram delivery ID, report, heartbeat, lock absence, and page cleanup before keeping the single daily schedule loaded.

## Measured outcome

- First wake `wake-7aef819a21c24d01047fb372`: durable `completed_no_effect / existing_bundles_reused`, Telegram ID `12758`, but native exit `1` incorrectly produced `worker_failed`.
- Repair `96277e017`: `applied_bundle` and `completed_no_effect` are exit `0`; circuit/invalid outcomes remain non-zero.
- Verification wake `wake-44eb04e69ececde08a73a2d1`: `completed_no_effect / existing_bundles_reused`, Telegram ID `12782`, `worker_finished`, launchd exit `0`.
- Final provider audits: Doorkeeper `eligible=4/calendar_free=0`, Eventbrite `eligible=0/calendar_free=0`, TECH PLAY `eligible=3/calendar_free=0`.
- Applied bundles stayed `13→13`, Calendar/evidence delivery counts stayed unchanged, the Connector page closed, the exact four pre-existing pages survived, and no lock remained.
- TECH PLAY's first real `applied_bundle` remains conditional on a future non-conflicting candidate; safety gates are not weakened to manufacture acceptance.
