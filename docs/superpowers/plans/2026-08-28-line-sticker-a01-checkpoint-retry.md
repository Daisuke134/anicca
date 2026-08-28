# LINE Sticker A01 Checkpoint Retry Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan.

**Goal:** Remove the fixed disk threshold and prove a failed local write preserves the prior checkpoint so the same item can retry.

**Spec:** `docs/superpowers/specs/2026-08-28-line-sticker-loop-design.md`, atomic TODO A01.

**Files:**
- Modify: `skills/earn/line-sticker/line_sticker_media.py`
- Modify: `skills/earn/line-sticker/tests/test_line_sticker_media.py`

## Task 1

- [ ] Replace the old disk-gate test with a failing test that patches reported free space to zero and proves a normal planning stage still runs; no fixed-capacity API or environment variable is consulted.
- [ ] Add a failing write-recovery test: preserve an existing checkpoint, force `os.replace` to raise `OSError(errno.ENOSPC)` during the next atomic write, assert `disk_full`, assert the prior bytes are unchanged, then retry without the fault and assert the same destination receives the new bytes.
- [ ] Run the two tests and confirm RED against the current fixed gate/current test contract.
- [ ] Delete `_disk_gate`, every call to it, `LINE_STICKER_MEDIA_HEADROOM_BYTES`, and imports used only by that gate. Do not add an estimator, cleaner, quota, configuration option, or background service.
- [ ] Keep shared emergency stop-file behavior out of this media tool; the installed outer loop already owns host-wide stop policy.
- [ ] Run the focused media suite, then the existing validator/owner suites. Confirm no behavior other than fixed disk gating changed.
- [ ] Commit and push only the two owned files with message `fix(line-sticker): retry failed media writes`.

## Acceptance

- No fixed disk threshold or disk-capacity environment variable remains in production or tests.
- A forced `ENOSPC` cannot replace/corrupt an existing checkpoint.
- Retrying the same write succeeds after the temporary failure clears.
- No external effect occurs in the failure test.
