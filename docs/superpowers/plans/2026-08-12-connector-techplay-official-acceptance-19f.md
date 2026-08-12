# TECH PLAY Official Launchd Acceptance Plan

**Goal:** Use the existing launchd owner exactly once to prove a real connector bundle through discovery, application, registered readback, Calendar, immutable evidence, Telegram, and owned-page cleanup.

## Preflight evidence

- Branch/worktree is clean and pushed through SSOT commit `2077c3519`.
- `gui/501/ai.anicca.life-manager-connector-native` is loaded, points to this exact worktree, is not running, has no owner lock, and has a single daily `09:00` trigger.
- Contrary to the older chat statement, the production schedule is currently loaded; this plan records the measured state instead of preserving that contradiction.
- Shared CDP `127.0.0.1:9222` has exactly four pre-existing page targets; all must survive unchanged.
- Prior durable result is `completed_no_effect / provider_discovery_failed / consecutive_failure_count=2`; prior logs are historical and do not prove the current build.

## Acceptance contract

- [ ] Announce and execute exactly one `launchctl kickstart gui/501/ai.anicca.life-manager-connector-native` without `-k`, plist reinstall, or manual executor.
- [ ] Observe one new wake ID and bounded termination; no concurrent owner and no stale lock.
- [ ] A successful TECH PLAY acceptance requires `applied_bundle`, provider `techplay`, provider status `registered`, one final action, one Calendar event with exact canonical URL, valid receipt/PNG, Telegram message/photo receipts, and bundle/checkpoint readback.
- [ ] Preserve all four pre-existing page targets and close only the connector-owned page.
- [ ] If the wake completes without a non-conflicting TECH PLAY candidate, report the exact provider outcome; do not claim application success.
- [ ] If the wake fails or effects are unknown, unload the daily schedule before repair/retry so no unattended mutation can occur.
- [ ] On success, independently re-read Calendar, evidence files, Telegram delivery IDs, report, heartbeat, lock absence, and page cleanup before keeping the single daily schedule loaded.
