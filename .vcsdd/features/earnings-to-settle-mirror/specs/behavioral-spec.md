---
feature: earnings-to-settle-mirror
mode: lean
sprint: 1
language: python
created: 2026-07-01
parent_goal: GOAL-sprint-4-M1-M2.md — feature (a) reframed
supersedes: naive "LAYER C settle wire" that would have modified gig-cli.sh
---

# Behavioral Specification — earnings-to-settle-mirror (sprint-4 (a))

## 1. Purpose

Bridge `~/gig/earnings.jsonl` (written by the LAYER C tmux inner core when a
Coconala 検収/支払 event is detected) into `~/loops/gig/settle.jsonl` so the
reconciler (feature (b)) can populate `roi_jpy_realized`.

Runs as a menu item ("settle-mirror") on 3600s cadence, ROI=0 (lowest
priority), reads `~/gig/earnings.jsonl` (READ-only per INV-4), writes ONLY
to `~/loops/<slot>/settle.jsonl` and its offset marker.

## 2. Design decision: mirror pattern (NOT modify LAYER C tmux)

Rejected approach: modifying `gig-cli.sh:21` STARTUP prompt to make the tmux
inner-core claude session write `settle.jsonl` directly. Rejected because:
- Fragile: STARTUP is a giant single-line prompt; any edit risks breaking
  the earn loop that is currently producing 23 in-flight applications.
- INV-1 risk: modifying LAYER C requires restarting the tmux session.
- Not needed: LAYER C already writes `~/gig/earnings.jsonl` on 検収
  detection; we just mirror it.

Chosen approach: a menu-item-driven mirror. The dispatcher picks the
mirror item on its 3600s cadence, invokes `mirror_earnings_to_settle`
in-process (same pattern as reconciler, feature (b)), which reads new
earnings rows and appends corresponding settle rows.

## 3. Requirements (EARS)

### Group M — Menu integration (SAME pattern as reconciler)

- **REQ-M1**: THE production gig menu.json SHALL contain a
  `settle-mirror` item: `{name: "settle-mirror", category: "settle-mirror",
  platform: "internal", roi_estimate_jpy: 0, probability_of_landing: 1.0,
  expected_settlement_days: 0, required_budget: "LIGHT", blocker_check: null,
  min_cadence_seconds: 3600}`.
- **REQ-M2**: WHEN STEP 6 picks an item whose `category == "settle-mirror"`,
  the dispatcher SHALL:
  (a) invoke `mirror_earnings_to_settle(slot_dir, earnings_path, now_ts)`
      in-process (no subprocess),
  (b) NOT call `enqueue_task_descriptor` for this pick,
  (c) set the build_log outcome to
      `"settle-mirror:new=N/dup=M/unmatched=K"`,
  (d) `earnings_path` defaults to `~/gig/earnings.jsonl` when
      `slot == "gig"`; other slots defer to sprint-5.

### Group R — Mirror match/append

- **REQ-R1**: THE MIRROR SHALL be a PURE-callable Python function
  `mirror_earnings_to_settle(slot_dir: Path, earnings_path: Path, now_ts: int)
  -> MirrorReport` returning `{new: int, dup: int, unmatched_pass_id: int,
  elapsed_ms: int}`.
- **REQ-R2**: THE MIRROR SHALL read `earnings_path` from
  `state/settle-mirror-offset.json:last_earnings_line` (default 0) onward.
- **REQ-R3**: FOR EACH new earnings row where
  `status ∈ {"検収", "支払", "検収完了", "completed", "paid"}` AND
  `int(jpy) > 0`, THE MIRROR SHALL:
  (i) parse the row's `requestId`,
  (ii) look up the matching `pass_id` by scanning
      `~/loops/<slot>/tasks/*.json` for a descriptor whose
      `picked.name` OR `picked.category` string CONTAINS the `requestId`,
      OR by scanning roi.jsonl for a row whose `outcome` string CONTAINS
      the `requestId`,
  (iii) append a row to `~/loops/<slot>/settle.jsonl`:
       `{schema_version:1, ts: now_ts, pass_id: <lookup-or-fallback>,
         slot, jpy: int(row.jpy), source: "coconala-earnings-mirror",
         evidence: {requestId, earnings_ts, earnings_status}}`.
- **REQ-R4** (fail-closed on unmatched pass_id): WHEN the lookup returns
  no match, THE MIRROR SHALL use
  `pass_id = f"unmatched-requestId-{row.requestId}"` so the reconciler
  will route the row to `.unmatched.jsonl` with reason `unknown-pass-id`.
  The mirror NEVER fabricates a valid-looking pass_id.
- **REQ-R5**: THE MIRROR SHALL dedup by `requestId + earnings_status`
  against the existing `settle.jsonl` tail (last 500 rows). If already
  present, skip and count in `dup`.
- **REQ-R6**: writes SHALL follow REQ-R5-equivalent ordering:
  (i) build in-memory settle-rows-to-append,
  (ii) append to `settle.jsonl` (POSIX per-line atomicity),
  (iii) write `state/settle-mirror-last-run.json` (report),
  (iv) LAST: write `state/settle-mirror-offset.json` atomically.
  If (iv) crashes, next run replays (ii)+(iii); (v) dedup in REQ-R5
  ensures no double-append.
- **REQ-R7**: THE MIRROR SHALL NEVER write to `~/gig/*` or any file
  outside `~/loops/<slot>/`.

### Group I — Invariants

- **REQ-I1** (INV-1 / INV-P1): no subprocess to `<slot>-cli.sh`, no
  `tmux kill`, no `--restart`.
- **REQ-I2** (INV-4): read-only access to `~/gig/earnings.jsonl`; writes
  ONLY under `~/loops/<slot>/`. Verified by SHA-256 hash of the earnings
  file before/after + source grep for any write-mode reference to
  `~/gig/` or `earnings.jsonl`.
- **REQ-I3** (INV-J8): no osascript / Telegram / Slack / Twilio / sudo /
  SecKeychain / Touch-ID / find-generic-password.
- **REQ-I4**: no `shell=True`, no `os.system`. argv-list subprocess only.
- **REQ-I5** (fail-closed): never fabricate a plausible pass_id;
  unmatched → `unmatched-requestId-<x>` sentinel that reconciler routes
  to `.unmatched.jsonl`.

## 4. Edge cases

| EDGE | Trigger | Expected |
|---|---|---|
| E1 | `earnings_path` does not exist | report `{new:0, dup:0, unmatched_pass_id:0}`; no crash |
| E2 | Malformed earnings.jsonl line | skip that line; no append |
| E3 | Earnings row status not in the SETTLED set | ignored (in-flight, not settled) |
| E4 | Earnings row missing jpy or jpy=0 | ignored (must be > 0) |
| E5 | Multiple identical earnings rows (same requestId + status) | first wins; subsequent → `dup` |
| E6 | tasks/*.json contains a match but roi.jsonl doesn't | still emit settle with matched pass_id (roi row may not exist yet if this is the first cycle) |
| E7 | `settle.jsonl` doesn't exist yet | created on first append |
| E8 | Offset ahead of earnings.jsonl length (rotation) | reset offset to 0 |
| E9 | Match found in BOTH tasks/ AND roi.jsonl for same requestId | pass_id from tasks/ wins (tasks/ is more direct) |

## 5. NFR

- **NFR-1**: wall-time < 500 ms for < 10k earnings rows + < 100k tasks/ files.
- **NFR-2**: no new external deps.
- **NFR-3**: dedup lookup is O(tail) not O(full-file).
</parameter>
