# Affiliate Tool Receipt Self-Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Affiliate loop bound its own `tool-attempt-receipts.jsonl` growth without deleting confirmed or uncertain external-effect evidence.

**Architecture:** The Affiliate owner rotates only old `NO_EFFECT` and `READ_ONLY_CONFIRMED` operational rows when its ledger exceeds 32 MiB. It keeps protected effect rows and the newest 8 MiB of operational rows in the active ledger, writes older disposable rows to bounded gzip archives, and performs rotate→reopen→dedupe→append while holding one stable sibling lock file.

**Tech Stack:** Python 3 standard library (`fcntl`, `gzip`, `json`, `os`, `tempfile`), `unittest`.

## Global Constraints

- Do not change the Atomic TODO Register order.
- Do not add another launchd job or cleanup framework.
- Preserve `EFFECT_CONFIRMED`, `UNKNOWN`, malformed rows, credentials, sessions, buyer artifacts, ledgers outside this exact owner, and every open/leased path. Only `NO_EFFECT` and `READ_ONLY_CONFIRMED` rows are operationally disposable.
- Rotation failure must preserve the existing ledger and fail the append; it must never silently discard a receipt.
- Production target: at most two files and 100 production LOC.

---

## File Structure

- Modify `skills/affiliate/scripts/local_loop.py`: owner-local classification, gzip rotation, atomic active-ledger replacement, and append-path invocation.
- Modify `skills/affiliate/tests/test_local_loop.py`: focused preservation, bounded archive, replay, and failure regressions.
- Update `docs/superpowers/specs/2026-08-20-life-manager-disk-cleanup-loop-design.md` only after production readback, recording measured bytes and the next unchanged atom.

### Task 1: Bound Affiliate tool-attempt operational receipts

**Files:**
- Modify: `skills/affiliate/scripts/local_loop.py:77-103`
- Modify: `skills/affiliate/scripts/local_loop.py:1329-1380`
- Test: `skills/affiliate/tests/test_local_loop.py:1669`

**Interfaces:**
- Consumes: `append_unique(path: Path, value: dict, identity: tuple[str, ...]) -> bool` and the existing `effect_certainty` field.
- Produces: `rotate_tool_attempt_receipts(path: Path, *, max_bytes: int = 32 * 1024 * 1024, recent_no_effect_bytes: int = 8 * 1024 * 1024, keep_archives: int = 4) -> dict[str, int]`; caller holds `<path>.lock` throughout.
- Produces archives: `<state>/tool-attempt-receipts.archive-<UTC timestamp>.jsonl.gz`, mode `0600`.

- [ ] **Step 1: Write the failing preservation and bound test**

Add one test that writes old `NO_EFFECT`, one `EFFECT_CONFIRMED`, one `UNKNOWN`, and one malformed line; invokes `rotate_tool_attempt_receipts(..., max_bytes=512, recent_no_effect_bytes=128, keep_archives=2)`; then asserts:

```python
self.assertIn("EFFECT_CONFIRMED", active)
self.assertIn("UNKNOWN", active)
self.assertIn("malformed", active)
self.assertLessEqual(len(list(state.glob("tool-attempt-receipts.archive-*.jsonl.gz"))), 2)
self.assertGreater(result["archived_rows"], 0)
self.assertEqual(result["protected_rows"], 3)
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
python3 -m unittest skills.affiliate.tests.test_local_loop.LocalLoopTest.test_tool_attempt_rotation_preserves_external_effect_evidence
```

Expected: `ERROR` because `rotate_tool_attempt_receipts` does not exist.

- [ ] **Step 3: Implement the minimal owner-local rotation**

Implement the exact contract:

```python
def rotate_tool_attempt_receipts(path, *, max_bytes=32 * 1024 * 1024,
                                 recent_no_effect_bytes=8 * 1024 * 1024,
                                 keep_archives=4):
    # Return zero counters below max_bytes.
    # Under the caller's stable sibling-file lock, classify only valid rows whose
    # effect_certainty in {"NO_EFFECT", "READ_ONLY_CONFIRMED"} as disposable.
    # Preserve confirmed/unknown/malformed rows in the active file.
    # Preserve the newest recent_no_effect_bytes of disposable rows.
    # gzip older disposable rows to a 0600 temporary, fsync, then os.replace.
    # Atomically rewrite and fsync the active ledger before pruning only
    # excess owner-created gzip archives beyond keep_archives.
```

For this exact ledger, acquire and fsync a mode-0600 stable sibling `tool-attempt-receipts.jsonl.lock`, then rotate, reopen the current ledger path, scan identities, and append the new row while still holding that lock. Never continue writing through a file descriptor opened before `os.replace`. Other `append_unique` callers retain their current behavior. Do not change sibling loops.

- [ ] **Step 4: Add replay and failure regressions**

Add focused assertions that an immediate second rotation archives zero rows, and patch `gzip.open` or `os.replace` to fail before active replacement; assert the original ledger bytes remain identical and no completed archive is reported.

- [ ] **Step 5: Run GREEN verification**

Run:

```bash
python3 -m unittest skills.affiliate.tests.test_local_loop.LocalLoopTest.test_tool_attempt_rotation_preserves_external_effect_evidence
python3 -m unittest skills.affiliate.tests.test_local_loop.LocalLoopTest.test_tool_attempt_rotation_replay_is_noop
python3 -m unittest skills.affiliate.tests.test_local_loop.LocalLoopTest.test_tool_attempt_rotation_failure_preserves_ledger
python3 -m unittest skills.affiliate.tests.test_local_loop
git diff --check
```

Expected: all selected tests pass, full Affiliate loop module exits `OK`, and `git diff --check` exits 0.

- [ ] **Step 6: Commit and push the implementation branch**

```bash
git add skills/affiliate/scripts/local_loop.py skills/affiliate/tests/test_local_loop.py
git commit -m "fix: bound affiliate tool receipt growth"
git push origin HEAD
```

- [ ] **Step 7: Merge, release, and read back through the existing owner**

After merge to `main`, cut one immutable release from pushed `origin/main`, apply only `ai.anicca.affiliate-loop` through `bin/lm-loop`, and require one natural terminal wake. Record before/after bytes, archive count, last exit, `protected_deletions=0`, and exact release SHA. Do not restart Coconala or any sibling loop.

- [ ] **Step 8: Update the spec without advancing past unverified work**

Mark only this owner result under `All-loop bounded-output audit`. Keep the active cursor on the same audit and measure the next largest unbounded owner before selecting its implementation slice.

## Self-Review

- Spec coverage: this plan covers only the first measured owner, as required by one-active-item ordering; capacity claims and Coconala lane-specific producer contracts remain later atoms.
- Placeholder scan: every implementation and verification step contains an exact interface or command.
- Type consistency: the rotation function accepts `Path` and integer byte/archive limits and returns integer counters used directly by the tests and receipt update.
