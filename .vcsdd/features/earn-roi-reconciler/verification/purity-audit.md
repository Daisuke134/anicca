---
feature: earn-roi-reconciler
phase: 5
mode: lean
generated_at: 2026-07-01
---

# Purity Boundary Audit — earn-roi-reconciler

## Declared Boundaries

| Layer | Symbol | Side effects |
|---|---|---|
| PURE — `lib/reconciler.py` | `parse_settle_line(line)` | none (str → dict\|None) |
| PURE — `lib/reconciler.py` | `merge_realized(existing, new)` | none (int, int → int, str) |
| I/O — `lib/reconciler.py` | `reconcile(slot_dir, now_ts)` | reads settle.jsonl + roi.jsonl + .unmatched.jsonl tail; writes roi.jsonl (atomic) + .unmatched.jsonl (append) + state/reconciler-last-run.json + state/reconciler-offset.json |
| ORCHESTRATOR — `proactive-loop-dispatch.py` STEP 6 branch | invokes reconcile in-process when picked.category == "reconciler"; skips enqueue_task_descriptor | 1 conditional, ~10 lines, tested by 4 integration tests |

## Observed Boundaries

- Both PURE functions verified side-effect-free (parametrized tests over their input domain).
- reconcile() write ordering per REQ-R5 (i)-(v) proven by test_reconcile_atomic_replace_leaves_old_roi_on_write_crash monkeypatching os.replace to raise on first call.
- Dispatcher branch verified by 4 integration tests (in-process invoke, tasks/ untouched, build_log outcome, INV-4 SHA proof).
- No writes to ~/gig confirmed by static grep + live E2E SHA-256.

## Summary

Purity boundary clean. Dispatcher patch scope is exactly 1 branch + 1 next_candidate conditional (< 15 lines total) as spec architecture declares. All I/O confined to `~/loops/<slot>/`.
</parameter>
