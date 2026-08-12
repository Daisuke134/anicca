# Connector KokuchPro durable audit 20F1 implementation plan

> **Execution:** Ponytail `full` keeps this slice to the existing production operations seam. Implement with Superpowers TDD; Sol plans/verifies/updates SSOT/commits/pushes, Luna edits production/tests, fresh Sol reviews Critical/Important.

**Goal:** Persist KokuchPro's privacy-safe five-stage discovery counts before connecting its default production workflow.

**Architecture:** Add one provider-specific append-only file and one returned recorder to `createMinimalProductionOperations`, reusing the existing strict five-count validator used by Eventbrite/TECH PLAY. Store only schema/wake/counts/timestamp in a 0600 JSONL file. No URL, title, ticket, auth state, private value, browser, workflow, router, native order, or schedule change.

**Ponytail size gate:** production about 3 LOC, test about 30–45 LOC, exact operations production/test 2 files.

## Task 1 — TDD KokuchPro aggregate audit

RED proves the recorder is missing. GREEN proves one valid frozen aggregate append, exact keys/mode, rejection of extra/missing/noninteger/out-of-order/>500 values without a second append, and no sensitive text. Run operations tests, syntax, diff check, fresh review.
