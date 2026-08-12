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

## First run result

- Wake `wake-9bb615ee5684f064d329e016` ended safely with `circuit_open / effect_unknown`, consecutive failures 2, bundle delta zero, report delta one, delivery delta one, positive Telegram provider ID `11062`.
- Cleanup, Git, CDP, and unloaded-label invariants passed.
- Acceptance failed because Peatix returned 18 Calendar-free candidates in search order; an unprocessed candidate became ambiguous before the exact same-event Calendar-covered accepted bundle candidate was visited.
- No second wake was started. Repair plan: `docs/superpowers/plans/2026-08-11-connector-peatix-existing-first-13c.md`.

## Second run result

- Wake `wake-b3f05e7a9c4a5afc322e3d2d` proved live existing-bundle reuse and later-candidate continuation with Submit zero for both registered Peatix candidates.
- Later event `5065833` durably reached provider receipt/PNG, Calendar exact event/readback, and Telegram message ID `11079`; photo delivery then failed.
- Item 12 checkpoints preserved the partial lineage, but the thrown evidence error bypassed terminal `reportWake`, producing report/delivery delta zero and exit 2.
- Cleanup and unloaded schedule invariants passed. Repair plan: `docs/superpowers/plans/2026-08-11-connector-evidence-error-report-13c.md`.

## Recovery run result

- Pushed repair commit `25d8e423d` ran through official `skills/connector/run.sh` exactly once as wake `wake-21bc904af45627b27b6f0277`; all four schedules remained unloaded.
- The wake reached Peatix event `5065833` by parent pre-readback `registered` and executed zero cache/direct/Harness Submit actions. It reused the immutable message checkpoint and provider ID `11079`, delivered only the missing photo as positive ID `11089`, and created exactly one final bundle.
- Bundle count changed `3→4`, wake reports `100→101`, and wake-report deliveries `112→113`. The terminal status was `applied_bundle`, consecutive failures zero, with positive report delivery ID `11090`.
- Independent validation found exactly one current Google Calendar event for the canonical idempotency marker and the same bundle event ID. Bundle digest/filename, provider receipt identity, PNG SHA/signature, message-to-photo lineage, regular-file/no-symlink checks, and mode 0600 all passed.
- The saved message checkpoint SHA and mtime were unchanged, proving message resend zero. The process exited zero; lock/process/owned page were removed; CDP returned to the original single newtab; Git remained clean/upstream `0/0`; all four labels returned unloaded. Together with the second run's exact existing-bundle reuse and same-page continuation, Item 13 acceptance is complete.
