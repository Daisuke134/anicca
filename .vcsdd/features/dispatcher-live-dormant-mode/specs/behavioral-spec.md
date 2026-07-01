---
feature: dispatcher-live-dormant-mode
mode: lean
sprint: 1
language: python
created: 2026-07-01
parent_goal: GOAL-sprint-4-M1-M2.md — feature (c)
---

# Behavioral Specification — dispatcher-live-dormant-mode (sprint-4 (c))

## 1. Purpose

Sprint-2's `is_dormant_with_horizon` PURE helper (from sprint-3 #34) is
currently NOT called from the dispatcher — the sentinel is never written
regardless of ROI reality. Sprint-4 (c) wires it behind a LIVE-MODE flag:
the dispatcher may consider dormant status ONLY when the slot has at least
one row in `roi.jsonl` with `roi_jpy_realized > 0` in the last 90 days.

This preserves parent §7b patience while unlocking real dormancy detection
once M2 fires (real ¥ actually settles).

## 2. Out of scope

- Does NOT re-implement `is_dormant_with_horizon` — that PURE helper already
  ships in `lib/quota_tracker.py`.
- Does NOT auto-write the sentinel today for slots without real settles;
  such slots stay in scaffold mode until M2 fires.
- Does NOT remove the sprint-2 `is_dormant()` helper (backward compat).

## 3. Requirements (EARS)

### Group L — Live-mode gate

- **REQ-L1**: THE PURE HELPER
  `has_realized_in_window(roi_rows: list[dict], now_ts: int, window_days: int = 90)
  -> bool` SHALL return True iff at least one row satisfies:
  `int(row.get("roi_jpy_realized", 0)) > 0 AND
   (now_ts - int(row.get("ts", 0))) <= window_days * 86400`.
- **REQ-L2**: THE PURE HELPER
  `compute_dormant_state(roi_rows: list[dict], slot_age_days: float,
   time_horizon_days: int, now_ts: int) -> dict` SHALL return
  `{"live_mode": bool, "consecutive_neg_windows": int, "is_dormant": bool}`.
  - `live_mode = has_realized_in_window(roi_rows, now_ts, window_days=90)`
  - When `live_mode == False`: `is_dormant = False` (unconditionally — slot
    has never settled, cannot be judged dormant)
  - When `live_mode == True`:
    `is_dormant = is_dormant_with_horizon(
       consecutive_neg_windows=<computed from roi_rows>,
       slot_age_days=slot_age_days,
       time_horizon_days=time_horizon_days,
     )`
- **REQ-L3**: `consecutive_neg_windows` computation from roi_rows: read the
  last `2 * time_horizon_days` daily windows (each window = 86400s ending
  at `now_ts`); for each window sum `roi_jpy_realized - roi_jpy_expected`;
  call `count_consecutive_negative_windows(list, most-recent-first)`. If
  fewer than `time_horizon_days` windows are present, return 0 (not enough
  history to judge).

### Group D — Dispatcher wire

- **REQ-D1**: STEP 3 health-check (post-existing recipe execution) SHALL
  invoke `compute_dormant_state` when `~/loops/<slot>/roi.jsonl` exists.
- **REQ-D2**: IF `compute_dormant_state()["is_dormant"] == True` AND
  `~/loops/<slot>/.dormant.sentinel` does NOT yet exist, THE DISPATCHER
  SHALL call `write_dormant_sentinel(slot_dir, evidence={...})` with an
  evidence dict `{ts, live_mode, consecutive_neg_windows, slot_age_days,
  time_horizon_days, window_days: 90}`.
- **REQ-D3**: THE DISPATCHER SHALL NEVER remove an existing
  `.dormant.sentinel` (spec sprint-3 #34 REQ-D5 already documents this).
- **REQ-D4** (fail-closed): IF `compute_dormant_state()` raises for any
  reason, the dispatcher SHALL log `step="3-dormant-check-error-<Exception>"`
  and CONTINUE the tick without writing a sentinel.

### Group I — Invariants

- **REQ-I1** (INV-P2): live-mode gate PREVENTS sprint-3 #34 residual risk
  of firing sentinel prematurely on slots that have never settled.
- **REQ-I2** (INV-1 / INV-P1): no subprocess to LAYER C; no tmux kill.
- **REQ-I3**: pure helpers are side-effect-free.

## 4. Edge cases

| EDGE | Trigger | Expected |
|---|---|---|
| E1 | `roi.jsonl` missing | live_mode=False → is_dormant=False |
| E2 | All roi rows have realized=0 | live_mode=False → is_dormant=False (M1 not reached) |
| E3 | roi row's `ts` is older than 90d + realized>0 | live_mode=False (out of window) |
| E4 | Slot very new (age < 2*horizon) | is_dormant_with_horizon returns False → no sentinel |
| E5 | Sentinel already exists | do NOT overwrite (idempotent) |
| E6 | Malformed roi row | skip that row during scan; no crash |
| E7 | roi_jpy_expected missing | treat as 0 for window sum |

## 5. NFR

- **NFR-1**: wall-time added < 20 ms per tick (linear scan of roi.jsonl).
- **NFR-2**: no new external deps.
- **NFR-3**: read-only on roi.jsonl.
</parameter>
