# Connector idempotent second foreground wake Item 13C plan

## Goal

Run the official minimal Connector once in the foreground while all Connector schedules remain unloaded, then prove the accepted existing bundle is reused with provider Submit zero, processing continues to a later candidate, one positive every-wake Telegram receipt is durable, and the owned process/page/lock are cleaned up.

## Preflight baseline

- Git HEAD `0f55ddf4c`, clean, upstream ahead/behind `0/0`.
- Native, healthcheck, Healer shadow, and host bridge labels all return unloaded (`launchctl` 113).
- `:9222` is healthy under the existing raw Chromium owner; no change is permitted to `:9223`, `:9226`, or `:9227`.
- Applied bundles: 3. Wake reports: 99. Wake-report delivery rows: 111.
- Existing exact bundles are two Luma and one accepted Peatix. Item 13A validates exact bundle/provider/artifact/current Calendar; Item 13B continues only on runtime `reused`.

## Execution

1. Snapshot safe line/file counts and process/lock/target baseline.
2. Invoke the official `skills/connector/run.sh` exactly once from the pushed worktree. Do not load a plist, create another browser/session, spawn a substitute executor, or run manual provider actions.
3. Watch the bounded foreground process until exit. Do not start a second wake.
4. Read only the new wake/action/discovery/delivery/bundle rows and official stderr/stdout. Validate the reused event lineage and next-candidate continuation.
5. Verify post-run Git clean/upstream `0/0`, four labels unloaded, Connector process/lock zero, no active owned-page lease, `:9222` healthy, and bundle/delivery deltas exact.

## Acceptance

- The official wake reads one exact existing applied bundle as `reused` after current provider and Calendar readback.
- For that event, cache/direct/Harness Submit actions are all zero. A later distinct candidate navigation/readback occurs on the same session/target/page lineage.
- A terminal wake report is written once and its Telegram delivery provider ID is positive. If a new candidate creates a bundle, it is exactly one new valid bundle; otherwise bundle delta is zero and the terminal safe status explains the later candidate outcome.
- No duplicate existing bundle, provider evidence, Telegram evidence message/photo, or Calendar create is produced for the reused event.
- Cleanup and unloaded schedule invariants hold.

## Close

Record exact wake ID, action/provider transitions, bundle/report/delivery deltas, positive IDs, and cleanup evidence in SSOT. Mark Item 13 complete only if every acceptance point passes; otherwise keep it open, plan the observed first failure, and repair with the same Sol-plan/Luna-build/review loop.
