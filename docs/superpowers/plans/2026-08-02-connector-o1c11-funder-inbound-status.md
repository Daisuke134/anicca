# O1C-11 Funder Inbound Status Implementation Plan

> **For agentic workers:** Use `executing-plans`, `building-agents`, and TDD inline. No subagents and no human confirmation pause.

**Goal:** Convert each source-bound inbound Gmail message into one auditable typed funder status: `delivery_failed`, `reply_received`, `rejected`, or `meeting_requested`.

**Architecture:** `gog` provides a fresh sanitized full Gmail thread. Deterministic code binds the inbound message to the original outreach, proves exact evidence quotes occur in that message, and hashes all semantic/raw fields before persistence. An explicit `agent_judgment` owns meaning. An append-only ledger plus a derived current-status view reflects the latest typed observation without mutable status rows.

## Task 1: Typed observation boundary

- [x] Write RED tests for all four statuses, exact quote binding, cross-thread/outbound refusal, unknown status, fabricated quote, and raw-data-free output.
- [x] Implement Gmail normalization and agent-judgment validation.
- [x] Re-run focused tests GREEN.

## Task 2: Append-only status projection

- [x] Write RED tests for tenant RLS, exact replay, one status per Gmail message, no UPDATE, and latest-observation current view.
- [x] Implement migration/store and add migration to local Compose.
- [x] Re-run focused and outbound regression tests GREEN.

## Task 3: Live YeetVC observation and evidence

- [x] Fresh-read all three Gmail threads; persist only the real YeetVC `delivery_failed` observation.
- [x] Verify DB current view, zero invented reply/meeting/rejection rows, JSON, diff, and unchecked count.
- [x] Commit implementation/docs separately, push, and verify local/remote HEAD equality.
