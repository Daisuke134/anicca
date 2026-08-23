# Paid One Owner At A Time Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Execute inline; do not dispatch subagents.

**Goal:** Ensure the Paid lane runs at most one project owner and one project effect path at a time.

**Architecture:** Reuse the current ordered `targeted_items` queue and `ThreadPoolExecutor`; change only the project executor factory to one worker. Readback remains serial and every project retains its existing isolated root, status, retry, and effect fences.

**Tech Stack:** Python 3.14, pytest, existing Paid executor.

## Constraints

- No new queue, database, service, process, provider branch, or customer effect.
- Existing priority sort and per-project isolation remain unchanged.
- A pending/failed/completed project returns before the next project owner begins.

### Task 1: Serialize Paid project owners

**Files:**
- Modify: `skills/earn/gig/scripts/paid_direct.py`
- Modify: `skills/earn/gig/tests/test_paid_remote_wait.py`

- [x] Add a RED behavior test that submits two instrumented tasks through the production project executor and observes maximum concurrency greater than one.
- [x] Add `_paid_project_executor()` returning the existing executor with exactly one worker and wire `run_once()` to it.
- [x] Run focused tests, `py_compile`, and the file-by-file regression gate.
- [ ] Commit, push to main, allow natural immutable release, and prove one wake never overlaps two project owners.
