---
feature: dispatcher-live-dormant-mode
phase: 5
generated_at: 2026-07-01
mode: lean
---

# Purity Boundary Audit — sprint-4 (c)

## Declared Boundaries

| Layer | Symbol | Side effects |
|---|---|---|
| PURE — `lib/quota_tracker.py` (append) | `has_realized_in_window` | none |
| PURE — `lib/quota_tracker.py` (append) | `compute_dormant_state` | none |
| I/O — `lib/quota_tracker.py` (existing) | `write_dormant_sentinel` | disk write |
| ORCHESTRATOR — `proactive-loop-dispatch.py` STEP block | inline dormant check | reads roi.jsonl, stats slot_dir, reads/writes .slot_created marker, conditionally writes .dormant.sentinel |

## Observed Boundaries

- `has_realized_in_window(roi_rows, now_ts, window_days=90)`: reads only args,
  returns bool. No disk I/O, no network, no globals. **Pure.**
- `compute_dormant_state(*, roi_rows, slot_age_days, time_horizon_days, now_ts)`:
  reads only kwargs, delegates to `has_realized_in_window` +
  `count_consecutive_negative_windows` + `is_dormant_with_horizon` (all pure).
  Returns dict. **Pure.**
- Dispatcher block: contains ONE side-effect call `write_dormant_sentinel(...)`
  guarded by REQ-D2 (`is_dormant AND not sentinel.exists()`), plus a marker
  file read/write for `.slot_created`. All I/O is confined to `slot_dir`
  (INV-4 preserved) and wrapped in try/except (REQ-D4 fail-closed).

## Summary

Purity boundary is intact. PURE helpers stay pure; the orchestrator block
sits in the acknowledged I/O layer with side effects confined to the slot
directory. No leakage between layers. No global mutable state added.
