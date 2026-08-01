# O1C-15 Submission-day Verification Implementation Plan

> **For agentic workers:** Use `executing-plans` inline. Do not pause for human confirmation.

**Goal:** Require same-day official verification of deadline, location, solo, terms, and eligibility before any funder submit.

### Task 1: Five-fact gate
- [x] RED then GREEN for one source-bound eligible same-day attempt.
- [x] Reject stale/fabricated/unlinked evidence, closed deadline, solo no/unknown, eligibility unknown/ineligible, and registry drift.

### Task 2: Immutable receipt
- [x] Add tenant/attempt-bound append-only gate ledger and exact-replay behavior.
- [x] Prove no raw official page or KIT content is persisted.

### Task 3: Live proof
- [x] Verify SPC from same-day official text and current application-kit without submitting.
- [x] Record evidence, mark O1C-15, count 97 remaining, push, and verify remote equality.
