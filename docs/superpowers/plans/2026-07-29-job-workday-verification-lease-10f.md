# Job Workday Verification Lease 10F Implementation Plan

> **Execution guard:** Use Superpowers test-driven-development and
> verification-before-completion. Only a claim before browser navigation may
> expire; any state at or after `navigation_started` remains terminal.

**Goal:** A process crash after claiming a Workday verification email but before
opening its URL self-heals on a later inbox pass, without allowing two browser
navigations or retrying an uncertain side effect.

**Architecture:** Treat `claimed` as a renewable visibility lease. Persist its
claim time and fence under the existing `BEGIN IMMEDIATE` transaction. A later
claim may replace the fence only after 900 seconds. The old worker must present
its old fence before `navigation_started`, so it fails closed after reclamation.
`navigation_started`, `opened`, and `navigation_unknown` never expire or retry.
Migrate existing private databases in place; a legacy claimed row falls back to
its `created_at`.

**Tech stack:** Python standard library (`datetime`, `sqlite3`, `uuid`) and
`unittest`.

## Sources

| Source | URL | Applied rule |
|---|---|---|
| Amazon SQS visibility timeout | https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html | “If you don't delete it before the timeout expires, the message becomes visible again.” Reclaim only pre-side-effect work after a bounded lease. |
| Celery Redis visibility timeout | https://docs.celeryq.dev/en/latest/getting-started/backends-and-brokers/redis.html#visibility-timeout | “wait for the worker to acknowledge the task before the message is redelivered.” A durable acknowledgment boundary separates retryable from terminal work. |
| Kubernetes Leases | https://kubernetes.io/docs/concepts/architecture/leases/ | The control plane uses `spec.renewTime` to determine availability. Persist time and replace holder identity/fence only after expiry. |

## Task 1 — RED: expired pre-navigation claim

- [x] Test that an immediate second claim is rejected.
- [x] Test that an expired `claimed` row receives a new fence.
- [x] Test that the old fence cannot cross `navigation_started`.
- [x] Test that the new fence can cross once and remains non-retryable afterward.
- [x] Test in-place recovery of a legacy database without `claimed_at`.
- [x] Run the focused test and capture the expected failure:
  `VerificationStore.claim()` rejects the new `now` argument in both recovery
  tests.

## Task 2 — GREEN: durable lease and migration

- [x] Add a `claimed_at` migration and a 900-second default lease.
- [x] Reclaim only expired `claimed` rows inside `BEGIN IMMEDIATE`.
- [x] Keep all at/after-navigation states terminal.
- [x] Document the executor contract in the inbox prompt.
- [x] Run focused and full suites: 6 focused, 163 job-loop, and 9 runner
  tests pass; Python compile and diff checks pass.

## Task 3 — GitHub and live reflection

- [x] Push, pass all CI, merge, and fast-forward canonical.
- [x] Kickstart only the existing inbox launchd job and verify exit zero,
  integrity, and no false-positive processing.
- [x] Update SSOT evidence. Keep the real Workday activation E2E pending until
  a new verification email arrives.

Live result: PR #1322 merged as `b17f838cd` after all seven required checks
passed in run `30454763988`. The canonical inbox advanced 15→16 with exit 0,
found no new recruiting email, and did not create a verification row or reopen
historical mail. Ledger and interview-prep integrity remain `ok`.
