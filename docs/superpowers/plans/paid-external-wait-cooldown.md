# Paid External Wait Cooldown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Execute inline; do not dispatch subagents.

**Goal:** Reuse a current validated external-wait receipt without launching the paid remote owner every five minutes, while periodically rechecking the official provider with the same project owner.

**Architecture:** Add one deterministic freshness predicate around the existing `validate_wait()` contract and apply it after DM synchronization but before semantic-decision model execution. A fresh wait immediately returns pending; an expired or hash-mismatched wait falls through to the existing semantic owner and official provider readback. The model still decides the external work; code owns only the timer and receipt validation.

**Tech Stack:** Python 3.14, pytest, existing Paid scripts.

## Global Constraints

- Paid only; no new service, database, scheduler, provider-name branch, or customer message.
- Default recheck interval is 3600 seconds; negative/future mtimes never count as fresh.
- New buyer feedback or changed requirements invalidates the cached wait through the existing hashes.
- Completion remains impossible from a cached wait; it can produce only nonterminal pending.

---

### Task 1: Bound unchanged provider rechecks

**Files:**
- Modify: `skills/earn/gig/scripts/paid_direct.py`
- Modify: `skills/earn/gig/tests/test_paid_remote_wait.py`

**Interfaces:**
- Consumes: validated `paid-remote-result.json` mtime and current feedback/requirements/digest.
- Produces: `_remote_wait_is_fresh(root, feedback, digest, now) -> bool` and `_remote_wait_before_decision(root, item, now) -> bool`; `_prepare_one()` returns the existing pending checkpoint before either decision or remote-owner model launch when true.

- [x] Write RED tests proving a current wait is fresh, a wait older than 3600 seconds is expired, and a future-dated receipt is rejected.
- [x] Run `python3 -m pytest skills/earn/gig/tests/test_paid_remote_wait.py -q` and observe missing `_remote_wait_is_fresh` failures.
- [x] Add the pure freshness predicate and call it before `validate_builder()` in `_run_remote_repair()`.
- [x] Move the effective fast path before semantic-decision execution after production showed per-wake decision drift invalidated the later cache.
- [x] Run focused tests plus `py_compile` GREEN.
- [x] Run all gig test files with the same per-file timeout gate and require no new failure file.
- [x] Commit, push to main, and let the existing release watcher publish naturally.
- [x] Prove a natural wake returns `18183618 pending/effect=0/readback=1` without changing the remote-owner summary mtime, qualification effect count, or Coconala seller messages.

Production evidence: release `7380faddd133e5731cf9b50f46a987d508f5b0b6` becomes `current` through the existing watcher. The natural wake starts the project at 03:36:00 and writes pending at 03:36:09. Decision summary remains at 03:17:07, remote-owner summary remains at 03:20:56, the qualification effect remains one row, the Coconala effect child is absent, and the official seller message hash remains unchanged.
