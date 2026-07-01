---
feature: earn-roi-reconciler
mode: lean
sprint: 1
language: python
created: 2026-07-01
parent_goal: GOAL-sprint-4-M1-M2.md — feature (b)
---

# Behavioral Specification — earn-roi-reconciler (sprint-4 (b))

## 1. Purpose

Match settle events (written by LAYER C into `~/loops/<slot>/settle.jsonl`)
back to the `roi.jsonl` row that spawned the work, and populate the
matching row's `roi_jpy_realized` field. This is the M1 consumer half of
sprint-4; the producer half (feature (a) LAYER C settle wire) ships after
this one so this one has fixtures to test against.

Runs as a **menu item** (per architecture spec §5b), NOT as a separate
launchd job — the proactive-loop tick picks it up when scheduling permits.
Cadence: 3600 seconds (hourly).

## 2. Out of scope

- Does NOT write `~/gig/earnings.jsonl` or any LAYER C ledger.
- Does NOT emit settle events; that's feature (a).
- Does NOT change `roi.jsonl` row shape; only fills in an existing field.
- Does NOT decide dormant status; that's feature (c).
- Does NOT touch LAYER C tmux cores.

## 3. Requirements (EARS)

### Group R — Reconciler match/update

- **REQ-R1**: THE RECONCILER SHALL be invocable as a PURE-callable Python
  function `reconcile(slot_dir: Path, now_ts: int) -> ReconcileReport` that
  reads `settle.jsonl`, matches rows by `pass_id`, updates `roi.jsonl`, and
  returns a report dict `{matched: int, unmatched: int, updated_rows: int,
  skipped_dup: int, elapsed_ms: int}`.
- **REQ-R2**: A settle row matches a roi row IFF the two share the SAME
  non-empty `pass_id` string. If the settle row has no `pass_id` or the
  value is empty, it goes to `.unmatched.jsonl` (see REQ-R7).
- **REQ-R3**: FOR EACH matched pair, THE RECONCILER SHALL set the roi row's
  `roi_jpy_realized` to `int(settle_row["jpy"])`. Non-integer or missing
  `jpy` in the settle row → treated as 0 (fail-closed; do NOT guess).
- **REQ-R4**: THE RECONCILER SHALL NEVER decrease an existing non-zero
  `roi_jpy_realized`. If the roi row already has `roi_jpy_realized > 0` and
  the new settle would set it to a lower value, the update is skipped and
  counted in `skipped_dup`. Same-value updates are idempotent (no-op).
- **REQ-R5**: THE RECONCILER SHALL rewrite `roi.jsonl` atomically:
  write to a tempfile in the SAME directory, then `os.replace`. NEVER
  leaves a partial `roi.jsonl` on disk.
- **REQ-R6**: THE RECONCILER SHALL append a marker line to
  `~/loops/<slot>/state/reconciler-last-run.json` on completion with the
  report dict + a monotonic run counter. This is the ONLY writes outside
  `.jsonl` files.
- **REQ-R7**: WHEN a settle row has no matching roi row (unknown pass_id,
  or no pass_id at all), THE RECONCILER SHALL append the settle row
  verbatim (plus a `{"reason": "..."}` field) to
  `~/loops/<slot>/.unmatched.jsonl`. This file is append-only.
- **REQ-R8**: THE RECONCILER SHALL track which settle rows have already
  been consumed via a monotonic offset stored in
  `~/loops/<slot>/state/reconciler-offset.json`: `{last_settle_line: int}`.
  On each run it reads settle.jsonl from `last_settle_line + 1` onward.
  Prevents replaying old settles into unmatched.jsonl on every run.
- **REQ-R9**: THE RECONCILER SHALL be safe to invoke concurrently with
  proactive-loop ticks (the proactive-loop lock is per-slot fcntl-based;
  the reconciler reads/writes the same slot dir). During its `os.replace`
  window, readers see either the old or the new file, never a partial.

### Group M — Menu integration

- **REQ-M1**: THE PRODUCTION menu.json for each of the 4 live slots
  (gig / clip / affiliate / bounty) SHALL contain an item:
  `{"name": "reconcile-earnings", "category": "reconciler",
    "platform": "internal", "roi_estimate_jpy": 0,
    "probability_of_landing": 1.0, "expected_settlement_days": 0,
    "required_budget": "LIGHT", "blocker_check": null,
    "min_cadence_seconds": 3600}`.
- **REQ-M2**: WHEN STEP 6 picks this item, the dispatcher SHALL invoke
  `reconcile(slot_dir, now_ts)` directly (in-process; no subprocess), then
  attach the returned report to the tasks/ descriptor as an extra
  `reconciler_report` field. The tasks/ descriptor is still enqueued for
  observability, but the actual reconciliation has already happened
  in-process; LAYER C does NOT dequeue reconciler tasks (they are marked
  `dequeue: false`).
- **REQ-M3**: The reconciler menu item SHALL use ROI=0 so it never wins
  the pick_next ranking by ROI; it only fires when its cadence (3600s)
  elapses AND all higher-ROI items have been cadence-excluded. This is
  intentionally the lowest-priority scheduled task.

### Group I — Invariants

- **REQ-I1** (parent INV-1 / INV-P1): The reconciler SHALL NOT stop, kill,
  or restart any LAYER C tmux core. No `tmux kill`, no `--restart`, no
  `subprocess` call to any `<slot>-cli.sh`.
- **REQ-I2** (parent INV-4): The reconciler SHALL write ONLY under
  `~/loops/<slot>/` (roi.jsonl, .unmatched.jsonl, state/*). NEVER writes
  `~/gig/earnings.jsonl`, `~/gig/*`, or any file outside `~/loops/`.
- **REQ-I3** (parent INV-J8): The reconciler SHALL NOT invoke osascript /
  terminal-notifier / Telegram / Slack / Twilio / sudo / SecKeychain /
  Touch-ID / find-generic-password / any human-touch surface.
- **REQ-I4**: The reconciler SHALL NOT use `subprocess.run(..., shell=True)`
  or `os.system`. Argv-list only.
- **REQ-I5**: The reconciler SHALL NEVER fabricate `roi_jpy_realized`.
  Ambiguous → `.unmatched.jsonl`.

## 4. Edge cases

| EDGE | Trigger | Expected |
|---|---|---|
| E1 | `settle.jsonl` does not exist | report `{matched:0, unmatched:0, ...}`; no crash |
| E2 | `roi.jsonl` does not exist | report `{matched:0, unmatched:N, ...}` where N = settle row count; all settles go to unmatched |
| E3 | Malformed line in `settle.jsonl` | skip that line; append to `.unmatched.jsonl` with reason `"malformed-json"`; continue |
| E4 | Malformed line in `roi.jsonl` | skip that line during scan; log to `state/reconciler-last-run.json.errors`; continue |
| E5 | Multiple settle rows for the SAME pass_id | first one wins per REQ-R4; subsequent count as `skipped_dup` |
| E6 | Settle row references a pass_id that doesn't exist in roi.jsonl | append verbatim to `.unmatched.jsonl` with reason `"unknown-pass-id"` |
| E7 | Reconciler crashes mid-write | REQ-R5 atomic replace ensures roi.jsonl is either untouched or fully updated |
| E8 | Empty `settle.jsonl` (just created) | report `{matched:0, unmatched:0}`; offset unchanged |
| E9 | Offset ahead of current file size (file rotated/truncated) | reset offset to 0, log to `state/reconciler-last-run.json` with warning `"offset-reset-file-shrank"` |

## 5. Non-functional

- **NFR-1**: Total wall-time < 500 ms per run for < 10k settle rows +
  < 100k roi rows. Larger files are OK (linear scan). No random-access
  requirement.
- **NFR-2**: No new external deps. Stdlib only.
- **NFR-3**: File permissions on rewritten `roi.jsonl` = 0644 (matches
  what sprint-3 roi.jsonl uses).

## 6. Sprint-4 handoff notes

- Feature (a) LAYER C settle wire produces `settle.jsonl` rows with the
  canonical shape `{schema_version:1, ts, pass_id, slot, jpy, source,
  evidence}`. This spec references that shape.
- Feature (c) dispatcher live-mode dormant reads roi.jsonl and checks for
  `roi_jpy_realized > 0` in the last 90 days. Once the reconciler
  populates that field, feature (c)'s gate can fire.
