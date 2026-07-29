# Job Inbox Budget Retry 10H Implementation Plan

> **Execution guard:** Use Superpowers test-driven-development and
> verification-before-completion. Only a runner exit 75 paired with the current
> evidence summary's exact `budget_blocked` status is normalized.

**Goal:** A token-budget-limited inbox pass exits cleanly for launchd while
acknowledging no candidate threads, so pending recruiting work retries on the
next 15-minute pass.

**Architecture:** Copy the already-live daily driver pattern. Temporarily disable
shell fail-fast only around the agent runner, capture its return code, and
restore fail-fast immediately. Normalize exit 75 to zero only when the
runner-owned current summary proves `budget_blocked`; every other nonzero result
propagates. Perform this check before resolving a result or marking any thread.

**Tech stack:** zsh, jq, existing agent-runner summary contract, and `unittest`.

## Sources

| Source | URL / command | Applied rule |
|---|---|---|
| `sysexits(3)` | local macOS manual | `EX_TEMPFAIL (75)` means a temporary failure whose request should be attempted later. |
| RFC 6585 §4 | https://www.rfc-editor.org/rfc/rfc6585#section-4 | Rate limiting is temporary and may communicate how long to wait before another request. |
| RabbitMQ Reliability Guide | https://www.rabbitmq.com/docs/reliability | A consumer should not acknowledge until it has completed the required work. |
| Existing daily driver | `apps/job-search-loop/scripts/run-daily.sh` | Production-proven copy+tweak: accept 75 only with a matching `budget_blocked` summary. |

## Task 1 — RED

- [x] Test inbox captures runner status without leaving fail-fast disabled.
- [x] Test only verified exit-75 `budget_blocked` normalizes to zero.
- [x] Test budget handling occurs before result resolution and acknowledgement.
- [x] Run focused test and capture the expected missing `set +e` runner boundary.

## Task 2 — GREEN

- [x] Apply the daily driver's exact bounded runner pattern to inbox.
- [x] Preserve all candidates as unseen on budget exhaustion.
- [x] Propagate every unverified/non-budget runner failure.
- [x] Run focused and full suites: 6 focused, 166 job-loop, and 9 runner
  tests pass; shell syntax and diff checks pass.

## Task 3 — GitHub and live reflection

- [ ] Push, pass all CI, merge, and fast-forward canonical.
- [ ] Verify the existing inbox launchd job remains healthy without fabricating
  a budget-blocked live event or touching seen state.
- [ ] Update SSOT evidence.
