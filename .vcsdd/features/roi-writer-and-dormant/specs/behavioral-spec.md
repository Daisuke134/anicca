---
feature: roi-writer-and-dormant
mode: lean
sprint: 1
language: python
created: 2026-07-01
updated: 2026-07-01 iter-1 scope cut per FIND-001
parent_spec: docs/superpowers/specs/2026-07-01-proactive-loop-architecture-and-cleanup-design.md
sprint2_carry: FIND-2-013 (dormant sentinel — DEFERRED to sprint-4 per FIND-001 below)
---

# Behavioral Specification — roi-writer-and-dormant (sprint-3 #34)

## 1. Purpose

Ship the sprint-3-actionable half of the two sprint-2-deferred pieces:

**Sprint-3 SHIPS**:
1. **Per-pass ROI tracker** — append a row to `~/loops/<slot>/roi.jsonl`
   at the end of every proactive-loop tick with the pass's ROI signal.
2. **Time-horizon lookup helper** — `resolve_time_horizon_days(menu)` +
   `is_dormant_with_horizon(...)` as PURE additions to `lib/quota_tracker`.

**Sprint-3 DEFERS to sprint-4** (per iter-1 FIND-001 scope cut):
- Automatic `.dormant.sentinel` write from the dispatcher. Reason: sprint-3
  ships `roi_jpy_realized=0` for every row (LAYER C dequeue + settle wire
  is sprint-4). `count_consecutive_negative_windows` counts strictly `< 0`
  values, so a sum of zeros never becomes negative → `is_dormant_with_horizon`
  is guaranteed False for the whole sprint-3 window. Wiring the write is
  DEAD CODE. Sprint-4 gets: settle wire from LAYER C → real realized values
  → real dormant math → sentinel write. The `is_dormant_with_horizon` PURE
  helper still ships in sprint-3 (it's stateless and unit-testable in
  isolation), just NOT called from the dispatcher.

## 2. Out of scope for sprint-3

- `.dormant.sentinel` auto-write from the dispatcher (deferred, see §1).
- Sentinel removal (= human/menu triggered; sprint-4).
- Cross-slot ROI reporting (sprint-4).
- Any change to LAYER C or `~/gig/` ledgers.

## 3. Requirements (EARS)

### Group W — Per-pass ROI writer (SHIPS sprint-3)

- **REQ-W1**: AT the end of every proactive-loop tick (= after STEP 7
  build_log append, before dispatcher exit), THE DISPATCHER SHALL append
  ONE line to `<slot_dir>/roi.jsonl` with the pass's ROI signal.
- **REQ-W2**: The row SHALL be a single JSON object with schema:
  `{schema_version: 1, ts: int, pass_id: str, slot: str, budget: str,
  picked: str|null, outcome: str, roi_jpy_realized: int (default 0),
  roi_jpy_expected: int (default 0)}`.
- **REQ-W3**: `roi_jpy_realized` SHALL be `0` in sprint-3 (LAYER C dequeue
  + settle wire is sprint-4 — see §1 for why this is scoped). `roi_jpy_expected`
  SHALL be `int(picked.roi_estimate_jpy × picked.probability_of_landing)`
  when a menu item was picked, else `0`.
- **REQ-W4**: Writes SHALL be best-effort append (open with `"a"` mode +
  write + close per row). If open/write raises OSError, log to
  core-status.json as `step=7-roi-write-failed-<ExceptionName>` and
  CONTINUE the tick (do NOT crash the dispatcher). Note: POSIX guarantees
  atomicity ONLY for writes ≤ PIPE_BUF (typically 512 B) to a pipe/FIFO;
  regular-file writes are NOT guaranteed atomic across concurrent writers.
  Sprint-3 relies on the fcntl re-entrancy guard in `proactive-loop.sh`
  (verified 2026-06-30) to serialize ticks within one slot; concurrent
  writes to the same `roi.jsonl` cannot happen by that construction.
- **REQ-W5**: `<slot_dir>/roi.jsonl` SHALL be append-only from the writer;
  the writer NEVER truncates, rewrites, or seeks non-terminal-EOF.

### Group T — Time-horizon lookup PURE (SHIPS sprint-3, no dispatcher wire)

- **REQ-T1**: THE PURE HELPER `resolve_time_horizon_days(menu, default=14)`
  SHALL return `int(menu.get("time_horizon_days", default))` when the
  parsed value > 0, else `default`. Handles missing key, None, negative,
  zero, non-integer castable-to-int, and non-castable inputs (fallback).
- **REQ-T2**: `is_dormant_with_horizon(consecutive_neg_windows: int,
  slot_age_days: float, time_horizon_days: int) -> bool` SHALL return True
  IFF BOTH: `slot_age_days > 2 * time_horizon_days` AND
  `consecutive_neg_windows > time_horizon_days`. This is the parent §7b
  INV-P3 canonical predicate. Both helpers ship as PURE + unit-tested in
  isolation; the DISPATCHER does NOT call them in sprint-3 (deferred).

### Group I — Invariants

- **REQ-I1** (parent INV-4 preserved): The ROI writer SHALL write ONLY
  `<slot_dir>/roi.jsonl`. Verified by mtime snapshot of everything under
  `<slot_dir>` EXCEPT `roi.jsonl` + `state/core-status.json` + `tasks/*` +
  `build_log.md` (= the pre-existing dispatcher writes).
- **REQ-I2** (parent INV-P1 preserved): No LAYER C tmux-kill / stop calls.
  Static grep + AST-import check on new files.
- **REQ-I3** (parent INV-P2 forbidden sentinel path): Sprint-3 dispatcher
  code path MUST NOT call `is_dormant()` (the 7-day sprint-2 helper) and
  MUST NOT call `write_dormant_sentinel()`. Grep guard test asserts 0
  occurrences of those two symbols in `proactive-loop-dispatch.py`.
  (The PURE helpers themselves remain callable from other code; the guard
  is on the DISPATCHER path only.)

## 4. Edge cases

| EDGE | Trigger | Expected |
|---|---|---|
| E1 | `<slot_dir>/roi.jsonl` does not exist | first write creates it (append mode) |
| E2 | roi.jsonl disk full / permission denied | log `step=7-roi-write-failed-<exc>`; tick continues |
| E3 | menu.json has no `time_horizon_days` field | `resolve_time_horizon_days` returns default (14) |
| E4 | menu has `time_horizon_days: 0`, negative, or non-int | `resolve_time_horizon_days` falls back to default (14) |
| E5 | pass had no `picked` (= STEP 5 returned None) | roi_jpy_expected = 0, picked = null, outcome copied verbatim |
| E6 | picked missing `roi_estimate_jpy` or `probability_of_landing` | treat missing as 0, do not crash |
| E7 | picked.probability_of_landing > 1 or < 0 (menu.json malformed) | clamp to [0, 1] before multiplying |
| E8 | dispatcher runs on a slot with pre-existing roi.jsonl containing N rows | after tick, roi.jsonl has N+1 rows; the pre-existing N are byte-identical |

## 5. NFR

- **NFR-1**: Wall-time added < 20ms per tick (= 1 open+write+close per row).
- **NFR-2**: No new external deps.
- **NFR-3**: File permissions on newly-created roi.jsonl = 0644 (default umask); readable by user only for HOME-owned slot dirs.

## 6. Sprint-4 carry (documented for handoff)

- Wire LAYER C settle callback → dispatcher reads settle events → updates
  the LATEST roi.jsonl row's `roi_jpy_realized` (or appends a settle row).
- Call `is_dormant_with_horizon` from dispatcher after roi write.
- Consider redefining "negative window" per parent §7b INV-P2: a window is
  negative if `sum(expected) - sum(realized) > threshold × sum(expected)`
  (= "we should have earned N but got 0 → negative window") — not the naive
  `sum(realized) < 0` check.
- `slot_age_days`: use `min(st_ctime, st_birthtime)` on macOS (birthtime is
  ionly on APFS + fs_stat API; `st_ctime` is inode-change-time which is
  NOT creation time — verified by adversary FIND-002). Sprint-4 must pick
  a robust source: writing a `.slot-created.ts` sentinel on first tick and
  reading it thereafter is the simplest cross-platform option.
- 24-hour window boundary: sprint-4 must pin midnight-UTC vs local vs
  strict-24h-since-first-row. Sprint-3 does not depend on this because
  the dispatcher never buckets rows.
