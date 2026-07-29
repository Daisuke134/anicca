# Job Retry Fence 10C Implementation Plan

> **Execution guard:** Use Superpowers test-driven-development and
> verification-before-completion. This plan extends backlog Order 10; it does
> not claim that Ashby or Workday real-submit gates are complete.

**Goal:** A definitely pre-click `not_submitted` application can resume after
its blocker is resolved, while `submitted` and `submit_unknown` remain
non-retryable and every attempt remains auditable.

**Architecture:** Keep one current intent row per application for compatibility,
add an append-only `(intent_id, fence)` attempt history, and reuse the current
intent only by atomically incrementing its fence. A reopened claim must pass the
same fresh resume and ATS-evidence checks as a first claim. The state machine
allows only `not_submitted -> submit_claimed`; ambiguous or confirmed outcomes
never reopen.

**Tech stack:** Python standard library, SQLite `BEGIN IMMEDIATE`, `unittest`,
Markdown runtime contract.

## Constraints

- Never retry `submit_unknown` or `submitted`.
- Never infer or bypass a missing legal fact.
- A retry consumes a slot only after fresh resume and claim-ready ATS evidence
  pass validation.
- The old fence cannot complete the reopened attempt.
- Existing ledgers migrate in place and backfill current intent evidence without
  changing application counts or externally visible outcomes.

## Sources

| Source | URL | Applied rule |
|---|---|---|
| SQLite transactions | https://sqlite.org/lang_transaction.html | “No reads or writes occur except within a transaction.” Reopen, slot allocation, fence increment, state transition, and attempt append stay in one immediate transaction. |
| SQLite UPSERT | https://sqlite.org/lang_upsert.html | An UPSERT may update or no-op on a uniqueness conflict; retry behavior is explicit rather than deleting the unique current-intent identity. |
| Amazon Builders' Library — Making retries safe with idempotent APIs | https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/ | The idempotency identifier and its effect must be recorded atomically; the new fence distinguishes a safe new attempt from a duplicate completion. |

## Task 1 — RED: executable retry contract

- [x] Add tests proving a `not_submitted` attempt reclaims on a later day with
  the same intent id and incremented fence.
- [x] Prove the prior fence cannot complete the new attempt.
- [x] Prove `submitted` and `submit_unknown` do not reopen.
- [x] Prove append-only attempt history survives reopen and completion.
- [x] Run the focused tests and capture the expected failure.

## Task 2 — GREEN: atomic fenced reopen

- [x] Add and backfill `submission_attempts`.
- [x] Implement retryable-application discovery.
- [x] Extend `claim_submission` with the atomic `not_submitted` reopen path.
- [x] Update both current intent and append-only attempt status on completion.
- [x] Update the daily prompt to process durable retryable applications before
  fresh discovery, after revalidating blockers and evidence.
- [x] Run focused and complete job-loop tests.

## Task 3 — Real migration, state, and GitHub

- [x] Exercise the canonical ledger through a copied migration first.
- [ ] Fast-forward canonical only through GitHub PR after all CI gates pass.
- [ ] Verify live database integrity, unchanged application counts, and the
  existing launchd schedules/exits.
- [ ] Update the SSOT spec and redacted evidence with exact commits, CI, and
  runtime measurements.
