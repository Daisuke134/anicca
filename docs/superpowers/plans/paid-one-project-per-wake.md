# Paid One Project Per Wake Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Execute inline; do not dispatch subagents.

**Goal:** Allow at most one unresolved Paid project to enter its project worker during each natural wake, without starving the other projects.

**Architecture:** Reuse the shipped `paid_admission.plan()` and `record_decisions()` contracts: terminal/readback-only items close without consuming the work slot; unresolved candidates compete for the existing `max_orders=1` least-recently-admitted round robin. Only the admitted project is initialized/selected and submitted to the existing one-worker executor.

**Tech Stack:** Python 3.14, pytest, existing `paid_admission.py`, existing Paid executor.

## Constraints

- Do not add a cursor, database, provider-name rule, buyer-name rule, or hardcoded project ID.
- Preserve priority ordering, must-action override, customer partition, stuck probe and escalation behavior from `paid_admission.py`.
- Every skipped existing project receives the existing durable skip record; no skipped project starts decision/owner/effect work.

### Task 1: Wire the existing admission contract

**Files:**
- Modify: `skills/earn/gig/scripts/paid_direct.py`
- Modify: `skills/earn/gig/tests/test_paid_remote_wait.py`

- [x] Write RED tests that the admission wrapper returns exactly one of two candidates and rotates to the other after the first receives a real `queue_selected` event.
- [x] Extract the existing readback-only dispositions into one pure parent helper so they do not consume admission slots.
- [x] Collect unresolved candidates, call `paid_admission.plan(max_orders=1)`, record skip decisions, and start only the admitted project.
- [x] Run focused tests, `py_compile`, and the file-by-file regression gate.
- [x] Commit, push, publish through the existing watcher, and prove one natural wake creates at most one new project prepared result while skipped projects start no decision/owner model.

Production evidence: immutable release `eb3da7e8a640427bc8674129854cf0c017f20b97` becomes `current` through the existing watcher. Its first completed natural wake reports `status=pending`, `actionable=1`, `failed=0`, and `pending=6`. Exactly one prepared file receives a new mtime (`18130722`); unresolved `18169985`, `18128025`, `18178439`, `18062411`, `18183618`, and `18184558` report `queued`. The existing admission ledger appends `queue_skipped/pass_order_limit_reached` for skipped established projects.
