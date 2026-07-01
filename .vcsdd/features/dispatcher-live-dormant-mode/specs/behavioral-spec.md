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
- **REQ-L3** (FIND-001 + FIND-002 fix — align to existing helper contract):
  `consecutive_neg_windows` computation from roi_rows uses the sprint-3
  `count_consecutive_negative_windows(daily_roi_7day_jpy: list[float]) -> int`
  helper VERBATIM. That helper's contract (verified at
  `skills/_shared/lib/quota_tracker.py:69-81`) is:
  * input = list of 7-DAY ROLLING ROI values (each element is a
    `sum(roi_jpy_realized - roi_jpy_expected)` over a 7-day trailing
    window; NOT a single-day sum)
  * order = MOST RECENT LAST (helper uses `reversed()` to scan tail)
  * returns count of consecutive negatives at the tail

  Computation steps in `compute_dormant_state`:
  (i) Group roi_rows by the day their `ts` falls into (midnight-UTC
      boundary). Compute `daily_net[day] = sum(row.roi_jpy_realized) -
      sum(row.roi_jpy_expected)`.
  (ii) Build a list `rolling_7d` of `2 * time_horizon_days` entries. Each
       entry `rolling_7d[i]` = sum of `daily_net[day_i - 6 .. day_i]` (a
       7-day trailing window ending at day_i). Order: MOST RECENT LAST.
  (iii) Call `count_consecutive_negative_windows(rolling_7d)` — the helper
        scans from tail (most recent) backward, counting consecutive `< 0`
        values.
  (iv) If fewer than `time_horizon_days` complete rolling-7d windows exist
       (= slot too young), return 0 (not enough history).
  This matches sprint-3 #34 PROP-T2 semantics exactly.

### Group D — Dispatcher wire

- **REQ-D1** (FIND-2-001 fix — real line numbers + placement resolution):
  Actual dispatcher lines (verified 2026-07-01):
  * STEP 3 recipe execution block: lines 99-145
  * SKIP guard reads `.dormant.sentinel`: line 147-163
  * `menu = load_menu(...)`: line 169 (AFTER SKIP guard)
  * STEP 6 ACT begins: line 196

  Because `menu` is loaded at line 169 but we need `time_horizon_days`
  from it, the dormant check CANNOT be placed before line 147. The
  dispatcher SHALL invoke `compute_dormant_state` AFTER `menu = load_menu`
  at line 169 AND BEFORE STEP 6 ACT at line 196 (i.e., between lines 170
  and 195). Consequence: a sentinel written on tick T takes effect on
  tick T+1 (= next 5-min cron). This 1-tick delay is intentional — the
  sprint-4 goal is to avoid PREMATURE dormant sentinels; a bounded 5-min
  latency in enforcement is acceptable and preserves correctness.
  Alternative (moving menu load earlier) is out of scope for sprint-4
  because it touches unrelated dispatcher structure.
- **REQ-D1a** (FIND-004 + FIND-2-001 fix — sources at real line 169+):
  * `roi_rows` = parsed `~/loops/<slot>/roi.jsonl` (skip malformed rows;
    EDGE-E6).
  * `slot_age_days` = `(now_ts - slot_dir.stat().st_ctime) / 86400.0`
    (falls back to 0.0 if stat() raises; log to core-status).
  * `time_horizon_days` = `resolve_time_horizon_days(menu, default=14)`
    (sprint-3 #34 REQ-T1 helper) — called after menu is loaded at
    dispatcher line 169.
  * `now_ts` = `int(time.time())` (dispatcher's clock).
- **REQ-D2**: IF `compute_dormant_state()["is_dormant"] == True` AND
  `~/loops/<slot>/.dormant.sentinel` does NOT yet exist, THE DISPATCHER
  SHALL call `write_dormant_sentinel(slot_dir, evidence={...})` with an
  evidence dict `{ts, live_mode, consecutive_neg_windows, slot_age_days,
  time_horizon_days, window_days: 90}`.
- **REQ-D3**: THE DISPATCHER SHALL NEVER remove an existing
  `.dormant.sentinel` (spec sprint-3 #34 REQ-D5 already documents this).
- **REQ-D4** (fail-closed; FIND-005 scope): IF ANY of the following raises,
  the dispatcher SHALL log
  `step="3-dormant-check-error-<Exception>"` and CONTINUE the tick without
  writing a sentinel:
  (a) reading roi.jsonl (OSError, JSONDecodeError per row = SKIP that row
      per EDGE-E6, NOT the whole call; total-file OSError = log + continue),
  (b) slot_dir.stat() for slot_age_days (OSError → slot_age_days=0.0),
  (c) resolve_time_horizon_days(menu, default=14) — never raises by design
      but catch OSError/ValueError just in case,
  (d) compute_dormant_state itself,
  (e) write_dormant_sentinel (OSError → log + continue; sentinel absence
      is the safe default).
  The dispatcher NEVER aborts a tick due to a dormant-check failure.

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
