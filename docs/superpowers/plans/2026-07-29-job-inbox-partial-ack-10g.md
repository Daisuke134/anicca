# Job Inbox Partial Acknowledgement 10G Implementation Plan

> **Execution guard:** Use Superpowers test-driven-development and
> verification-before-completion. A thread is acknowledged only after the
> executor returns a schema-valid durable outcome for that exact thread.

**Goal:** A partially successful inbox pass marks only the Gmail thread IDs it
actually processed, leaving every unprocessed candidate visible to the next
15-minute pass.

**Architecture:** Extend the validated inbox result with a unique
`processed_thread_ids` array. After the agent runner succeeds, resolve its
fresh result path from the runner-owned summary. A deterministic acknowledgement
function verifies that the IDs are valid, unique, a subset of the scanned
candidates, and consistent with `processed_threads`; it then atomically merges
only those IDs into private seen state. Unknown IDs, mismatched counts, missing
results, or runner failure acknowledge nothing.

**Tech stack:** Python standard library (`json`, `pathlib`), JSON Schema, zsh,
and `unittest`.

## Sources

| Source | URL | Applied rule |
|---|---|---|
| AWS Lambda partial batch responses | https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-errorhandling.html | A partial batch response makes only failed messages visible again; acknowledge batch items individually rather than dropping the entire batch. |
| Google Pub/Sub exactly-once delivery | https://cloud.google.com/pubsub/docs/exactly-once-delivery | “No redelivery occurs after the message is successfully acknowledged.” Acknowledgement is the terminal boundary, not initial receipt. |
| RabbitMQ Reliability Guide | https://www.rabbitmq.com/docs/reliability | “A consuming application should not acknowledge messages until it has done whatever it needs to do.” Acknowledge only after durable processing. |

## Task 1 — RED: partial acknowledgement

- [x] Test that one processed ID marks only that candidate seen.
- [x] Test that an unprocessed candidate remains unseen.
- [x] Test that an unknown ID or count mismatch fails closed and marks nothing.
- [x] Test schema requires unique processed IDs.
- [x] Test the shell resolves the runner result and passes it to deterministic
  acknowledgement.
- [x] Run focused tests and capture expected failures: missing
  `mark_processed_threads`, missing result-path wiring, and missing schema field.

## Task 2 — GREEN: result-bound acknowledgement

- [ ] Implement strict candidate/result validation and atomic partial mark.
- [ ] Add `processed_thread_ids` to prompt and result schema.
- [ ] Resolve only the current runner result in `run-inbox.sh`.
- [ ] Keep runner failure and missing result fail-closed.
- [ ] Run focused and full suites.

## Task 3 — GitHub and live reflection

- [ ] Push, pass all CI, merge, and fast-forward canonical.
- [ ] Kickstart only the existing inbox launchd job and verify exit zero,
  integrity, and no false-positive processing.
- [ ] Update SSOT evidence; keep real partial-message E2E pending until a real
  pass contains multiple candidate threads with mixed outcomes.
