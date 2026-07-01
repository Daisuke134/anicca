---
feature: roi-writer-and-dormant
mode: lean
sprint: 1
language: python
created: 2026-07-01
parent_spec: docs/superpowers/specs/2026-07-01-proactive-loop-architecture-and-cleanup-design.md
sprint2_carry: FIND-2-013 (dormant sentinel auto-write)
---

# Behavioral Specification — roi-writer-and-dormant (sprint-3 #34)

## 1. Purpose

Wire the last two sprint-2-deferred pieces of proactive-loop:

1. **Per-pass ROI tracker** — append a row to `~/loops/<slot>/roi.jsonl`
   at the end of every proactive-loop tick with the pass's ROI signal.
2. **Time-horizon-aware dormant sentinel** — when the slot's trailing
   `time_horizon_days × 2` windows are all zero-settled, write
   `~/loops/<slot>/.dormant.sentinel` so future ticks skip STEP 6 (=
   parent INV-P2 / INV-P3 patience honor).

CRITICAL patience invariant (parent §7b): sprint-2's original 7-day dormant
threshold was WRONG for gig (Coconala settlement = 7-30 days). Sprint-3 #34
switches to the per-slot `time_horizon_days` field on menu.json.

## 2. Out of scope

- Does NOT change the recipe execution logic (= that is #33).
- Does NOT remove the `.dormant.sentinel` (sentinel removal is a separate
  human-triggered or menu-item action; sprint-4 spec).
- Does NOT wire cross-slot ROI reporting (= sprint-4).
- Does NOT modify LAYER C tmux cores or `~/gig/` ledgers.

## 3. Requirements (EARS)

### Group W — Per-pass ROI writer

- **REQ-W1**: AT the end of every proactive-loop tick (= after STEP 7
  build_log append, before dispatcher exit), THE DISPATCHER SHALL append
  ONE line to `<slot_dir>/roi.jsonl` with the pass's ROI signal.
- **REQ-W2**: The row SHALL be a single JSON object with schema:
  `{schema_version: 1, ts: int, pass_id: str, slot: str, budget: str,
  picked: str|null, outcome: str, roi_jpy_realized: int (default 0),
  roi_jpy_expected: int (default 0)}`.
- **REQ-W3**: `roi_jpy_realized` SHALL be 0 in sprint-3 (= LAYER C dequeue
  + settle wire is sprint-4). `roi_jpy_expected` SHALL be
  `picked.roi_estimate_jpy × picked.probability_of_landing` when a menu
  item was picked, else 0.
- **REQ-W4**: Writes SHALL be atomic-append (open with `"a"` mode + write
  + close per row). If open/write fails, log to core-status.json as
  `step=7-roi-write-failed-<Exception>` and CONTINUE (do NOT crash tick).
- **REQ-W5**: `<slot_dir>/roi.jsonl` SHALL be append-only from the writer;
  the writer NEVER truncates or rewrites existing rows.

### Group D — Dormant sentinel auto-write

- **REQ-D1**: AFTER writing the roi.jsonl row, THE DISPATCHER SHALL
  compute `is_dormant_with_horizon(consecutive_neg_windows,
  slot_age_days, time_horizon_days)` using the SLOT'S time_horizon_days
  (from menu.json's top-level field, default 14).
- **REQ-D2**: `consecutive_neg_windows` SHALL be computed by reading the
  last `time_horizon_days × 2` days of `roi.jsonl`, summing
  `roi_jpy_realized` per 24-hour window, and calling
  `count_consecutive_negative_windows` on the list (most recent first).
- **REQ-D3**: `slot_age_days` SHALL be computed as
  `(now_ts - slot_dir.stat().st_ctime) / 86400`. If `<slot_dir>` was
  created less than `time_horizon_days × 2` days ago, THE DISPATCHER
  SHALL NOT write a sentinel (= new slots deserve the horizon window).
- **REQ-D4**: WHEN `is_dormant_with_horizon` returns True AND
  `.dormant.sentinel` does NOT already exist, THE DISPATCHER SHALL call
  `write_dormant_sentinel(slot_dir, evidence={...})` with an evidence
  dict `{ts, slot, time_horizon_days, consecutive_neg_windows,
  slot_age_days, total_roi_jpy}`.
- **REQ-D5**: THE DISPATCHER SHALL NEVER remove an existing
  `.dormant.sentinel`. (Removal is out of scope; a healthy revival must
  be human- or menu-item-triggered — sprint-4.)

### Group T — Time-horizon lookup

- **REQ-T1**: THE PURE HELPER `resolve_time_horizon_days(menu, default=14)`
  SHALL return `int(menu.get("time_horizon_days", default))` when > 0,
  else `default`. This is the ONLY source of truth for the horizon.
- **REQ-T2**: `is_dormant_with_horizon(consecutive_neg_windows,
  slot_age_days, time_horizon_days)` SHALL return True IFF BOTH:
  `slot_age_days > 2 * time_horizon_days` AND
  `consecutive_neg_windows > time_horizon_days`. This is
  the sprint-3 patch of sprint-2's `is_dormant` per parent §7b.

### Group I — Invariants

- **REQ-I1** (parent INV-4 preserved): The ROI writer + dormant checker
  SHALL only write under `<slot_dir>/{roi.jsonl, .dormant.sentinel}`.
  NEVER writes under `<slot_dir>/state/`, `<slot_dir>/tasks/`,
  `<slot_dir>/build_log.md`, or anywhere outside `<slot_dir>`.
- **REQ-I2** (parent INV-P1 preserved): No LAYER C tmux-kill / stop
  calls. Static grep 0 hits on new files.
- **REQ-I3** (parent INV-P2): The dormant threshold MUST use
  `time_horizon_days × 2`, NEVER a universal 7-day value. Sprint-2's
  `is_dormant(consecutive_neg_7day_windows, age_days)` stays for
  backward compat but is NOT called by the new dispatcher path.

## 4. Edge cases

| EDGE | Trigger | Expected |
|---|---|---|
| E1 | `<slot_dir>/roi.jsonl` does not exist | first write creates it (append mode) |
| E2 | `roi.jsonl` disk full / permission denied | log `step=7-roi-write-failed-<exc>`; tick continues |
| E3 | menu.json has no `time_horizon_days` field | default = 14 (per REQ-T1) |
| E4 | `time_horizon_days: 0` or negative in menu | fallback to default 14 (per REQ-T1) |
| E5 | slot_dir just created (age < 2 × horizon) | NEVER write sentinel (REQ-D3) |
| E6 | `.dormant.sentinel` already exists | do NOT overwrite; skip write_dormant_sentinel call (idempotent) |
| E7 | roi.jsonl has fewer than 2 × horizon days of rows | consecutive_neg_windows = number of complete windows found; is_dormant False if incomplete |
| E8 | pass had no `picked` (= STEP 5 returned None) | roi_jpy_expected = 0, picked = null, outcome copied verbatim from build_log |

## 5. NFR

- **NFR-1**: Wall-time added < 100ms per tick (= reads at most 2 × horizon
  days of roi.jsonl, typically < 100 rows).
- **NFR-2**: No new external deps.
- **NFR-3**: Atomic append; on macOS/Linux, single write() of a JSON line
  (which fits in one page) is atomic per POSIX.
