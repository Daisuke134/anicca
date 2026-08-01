# O1C-13 Funder Daily-driver Implementation Plan

> **For agentic workers:** Use `executing-plans` inline. Do not pause for human confirmation.

**Goal:** Make the existing CloakBrowser daily-driver `http://127.0.0.1:9222` the only active browser transport for every funder form route.

**Architecture:** Extend the shared-context driver with an official-origin-bound funder page method. A route manifest enumerates every active provider; a validator rejects another browser ref, endpoint, or launch mode. Agents retain semantic form-filling judgment.

### Task 1: Shared funder page boundary
- [x] RED then GREEN: official HTTPS origin uses one shared context and closes only its owned page.
- [x] Reject credentials, origin mismatch, multiple contexts, and every endpoint except `:9222`.

### Task 2: Complete active route manifest
- [x] RED then GREEN: every route has the exact daily-driver ref/endpoint and no launch command.
- [x] Include YC and generic official-source-bound accelerator forms; run all regressions.

### Task 3: Live evidence
- [x] Prove `:9222` responds and no active funder route owns `:9223`.
- [x] Record evidence, mark O1C-13, count 99 remaining, commit/push, verify remote equality.
