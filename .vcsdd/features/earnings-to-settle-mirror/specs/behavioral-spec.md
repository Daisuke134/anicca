---
feature: earnings-to-settle-mirror
mode: lean
sprint: 1
language: python
created: 2026-07-01
updated: 2026-07-01 cycle-2 — full rewrite per iter-1 FIND-001 architecture
parent_goal: GOAL-sprint-4-M1-M2.md — feature (a) reframed
---

# Behavioral Specification — earnings-to-settle-mirror (sprint-4 (a))

## 1. Purpose

Bridge `~/gig/earnings.jsonl` (written by LAYER C on 検収 detection) into
`~/loops/gig/settle.jsonl` so feature (b) reconciler can populate
`roi_jpy_realized`.

**Critical architectural constraint (iter-1 FIND-001)**: `pass_id` (a
proactive-loop primitive: `p-<unix_ts>`) and `requestId` (Coconala's request
ID, e.g. `5123100`) live in DIFFERENT ID spaces. Neither `tasks/*.json` nor
`roi.jsonl` currently carries `requestId`; neither `applied.jsonl` nor
`earnings.jsonl` currently carries `pass_id`. The linkage MUST be
established by the ONLY component that sees both simultaneously: LAYER C
gig-cli.sh's tmux inner core, when it dequeues a task and applies it to a
specific Coconala request.

## 2. Sprint-4 scope split (honest)

Sprint-4 (a) ships TWO complementary halves:

**(a1) LAYER C STARTUP prompt update** — required for M2 to fire
automatically. gig-cli.sh's giant STARTUP prompt is modified to:
- Dequeue oldest `~/loops/<slot>/tasks/*.json`, read its `pass_id`.
- When B2 APPLY BROADLY posts an application, record the LINKAGE
  `{pass_id, requestId, ts}` in `~/loops/<slot>/state/task-request-map.jsonl`
  (append-only).
- When EARNED CHECK detects 検収 for a `requestId`, look up the matching
  `pass_id` in `state/task-request-map.jsonl` and write it into the
  `earnings.jsonl` row: `{ts, requestId, jpy, status, evidence, pass_id}`.
- Applied.jsonl row similarly gains `pass_id` (backward-compat additive
  field — old readers ignore it).
- Deploy: ONE controlled `gig-cli.sh --restart` in a maintenance window.
  This is the ONLY INV-1 exception the /goal allows: a controlled deploy,
  NOT a health-triggered restart during normal operation.

**(a2) Mirror menu item** — reads `~/gig/earnings.jsonl` for new settled
rows and appends corresponding rows to `~/loops/<slot>/settle.jsonl`. When
the earnings row has a `pass_id` field (post-(a1)-deploy), it is used
verbatim. When missing (pre-(a1)-deploy earnings rows), the row is emitted
with `pass_id = "unmatched-requestId-{requestId}"` sentinel, which
reconciler REQ-R7 routes to `.unmatched.jsonl` with reason
`"unknown-pass-id"`. The mirror NEVER fabricates a plausible pass_id.

## 3. Requirements (EARS)

### Group L — LAYER C STARTUP prompt update (a1)

- **REQ-L1**: The STARTUP prompt in `skills/earn/gig/gig-cli.sh` SHALL be
  extended (edit-in-place, no restructure) with:
  (i) a new pre-B1 step: read `~/loops/gig/tasks/` for the oldest
      `*.json` file, parse its `pass_id`, hold it as `CURRENT_PASS_ID` for
      this pass. If no task file, `CURRENT_PASS_ID = null`.
  (ii) B2 APPLY: after each apply, append
       `{ts, pass_id: CURRENT_PASS_ID, requestId, action:"applied"}` to
       `~/loops/gig/state/task-request-map.jsonl` (create if absent). No
       change to applied.jsonl schema in the STARTUP itself; the map is
       the linkage source.
  (iii) EARNED CHECK: when 検収 is detected for a requestId, look up the
       matching `pass_id` via `grep '"requestId": <X>'` on
       `~/loops/gig/state/task-request-map.jsonl` (last match wins). Add
       `pass_id: <found or null>` to the earnings.jsonl row.
- **REQ-L2**: STARTUP prompt SHALL NOT change the existing applied.jsonl
  / earnings.jsonl / lessons.jsonl SCHEMA in any way that breaks
  backward-compat readers. The `pass_id` additions are new fields, never
  renames or removals.
- **REQ-L3**: Deployment SHALL be a single `bash gig-cli.sh --restart`
  invoked ONCE at feature-a1 deploy time. This is a controlled INV-1
  exception documented in parent architecture spec §5b handoff notes.
  Post-restart, `bash gig-cli.sh --status` MUST return `ALIVE` within
  30 seconds. If not, the deploy is aborted (git revert; STARTUP goes
  back to pre-a1).

### Group M — Menu integration (a2, same pattern as reconciler)

- **REQ-M1**: `~/loops/gig/menu.json` SHALL contain a `settle-mirror` item
  with `category: "settle-mirror"`, `roi_estimate_jpy: 0`,
  `probability_of_landing: 1.0`, `required_budget: "LIGHT"`,
  `min_cadence_seconds: 3600`.
- **REQ-M2**: WHEN STEP 6 picks `category == "settle-mirror"`, the
  dispatcher SHALL:
  (a) invoke `mirror_earnings_to_settle(slot_dir, earnings_path, now_ts)`
      in-process,
  (b) NOT call `enqueue_task_descriptor` for this pick,
  (c) set build_log outcome to
      `f"settle-mirror:new={r['new']}/dup={r['dup']}/unmatched={r['unmatched']}"`
      where `r` is the returned report dict — the report field is named
      `unmatched` (top level, INT) so the formatter reads that key
      verbatim.
  (d) `earnings_path` defaults to `~/gig/earnings.jsonl` when
      `slot == "gig"`.

### Group R — Mirror match/append

- **REQ-R1**: `mirror_earnings_to_settle(slot_dir: Path,
  earnings_path: Path, now_ts: int) -> dict` SHALL return
  `{new: int, dup: int, unmatched: int, elapsed_ms: int}`.
- **REQ-R2**: THE MIRROR SHALL read `earnings_path` from
  `state/settle-mirror-offset.json:last_earnings_line` (default 0) onward.
- **REQ-R3**: FOR EACH new earnings row where `status ∈ {"検収", "支払",
  "検収完了", "completed", "paid"}` AND `int(jpy) > 0`:
  (i) parse `requestId`,
  (ii) LOOKUP pass_id: read the earnings row's `pass_id` field
       DIRECTLY (post-(a1)-deploy rows have it). If absent OR the field
       value does not look like a proactive-loop pass_id (regex
       `^p-\d+$`), fallback to
       `pass_id = f"unmatched-requestId-{requestId}"`. NO substring
       matching. NO scanning of tasks/*.json or roi.jsonl.
  (iii) build the settle row:
       ```
       {schema_version: 1, ts: now_ts, pass_id, slot,
        jpy: int(row.jpy), source: "coconala-earnings-mirror",
        requestId: <str>, earnings_status: <str>,
        evidence: {earnings_ts: <str>}}
       ```
       — `requestId` and `earnings_status` are TOP-LEVEL fields (not
       nested in evidence) so REQ-R5 dedup can scan them without
       parsing evidence.
  (iv) append the settle row to `~/loops/<slot>/settle.jsonl`.
- **REQ-R4** (fail-closed): the mirror NEVER fabricates a valid-looking
  pass_id. If the earnings row lacks pass_id or has a malformed one, the
  emitted settle row uses the `unmatched-requestId-<X>` sentinel and is
  counted in `unmatched`. The reconciler will route these to
  `.unmatched.jsonl` on the next tick.
- **REQ-R5**: THE MIRROR SHALL dedup by matching (requestId,
  earnings_status) against the last 500 top-level fields in
  `~/loops/<slot>/settle.jsonl`. Read the tail, extract `.requestId` and
  `.earnings_status`, skip appending if the pair already appears.
  Count these in `dup`.
- **REQ-R6** (writes ordering, honestly cross-referencing feature (b)
  reconciler REQ-R5 which defines the (i)-(v) atomic pattern):
  (i) BUILD in-memory settle-rows-to-append,
  (ii) APPEND to `settle.jsonl` (POSIX per-line atomicity),
  (iii) WRITE `state/settle-mirror-last-run.json`,
  (iv) LAST: WRITE `state/settle-mirror-offset.json` atomically
       (tempfile + os.replace). If (iv) crashes, next run re-processes;
       REQ-R5 dedup guarantees no double-append.
- **REQ-R7**: THE MIRROR SHALL NEVER write to `~/gig/*` or any file
  outside `~/loops/<slot>/`.

### Group I — Invariants

- **REQ-I1** (INV-1 / INV-P1): except for the ONE controlled
  `gig-cli.sh --restart` at (a1) deploy time (REQ-L3), NO subprocess
  invocation of `<slot>-cli.sh` and NO tmux-kill of any kind.
- **REQ-I2** (INV-4): mirror READS `~/gig/earnings.jsonl` (verified by
  SHA-256 before/after) and writes ONLY under `~/loops/<slot>/`. Source
  grep on `settle_mirror.py` for `earnings.jsonl` returns hits only in
  read-mode `open(...)` calls.
- **REQ-I3** (INV-J8): no human-touch surfaces.
- **REQ-I4**: no `shell=True`, no `os.system(`; argv-list only.
- **REQ-I5** (fail-closed sentinel): mirror uses
  `unmatched-requestId-<X>` sentinel; reconciler routes to
  `.unmatched.jsonl` with `reason: "unknown-pass-id"` — the round-trip
  proves the sentinel path works.

## 4. Edge cases

| EDGE | Trigger | Expected |
|---|---|---|
| E1 | earnings.jsonl missing | report `{new:0, dup:0, unmatched:0}` |
| E2 | malformed earnings line | skip, no append |
| E3 | status not settled OR jpy = 0 | ignore (in-flight) |
| E4 | earnings row has pass_id but it doesn't match `^p-\d+$` | fallback to unmatched sentinel |
| E5 | duplicate (requestId, earnings_status) | dup counter, no append |
| E6 | pre-(a1)-deploy earnings row (no pass_id field) | unmatched sentinel; reconciler routes to `.unmatched.jsonl` for human review |
| E7 | settle.jsonl missing | created on first append |
| E8 | offset > earnings.jsonl length | reset to 0 |

## 5. Sprint-5 handoff

- (a1) STARTUP prompt update leaves the applied.jsonl SCHEMA additive;
  full schema migration (typed columns, indexed lookup) is sprint-5.
- Time-based / fuzzy pass_id matching for pre-(a1) unmatched rows is
  sprint-5 (manual audit expected).
- clip / affiliate / bounty slots require their own STARTUP updates for
  category-specific `<slot>-cli.sh` files; sprint-5.

## 6. NFR

- **NFR-1**: mirror wall-time < 500 ms per invocation.
- **NFR-2**: no new external deps.
- **NFR-3**: (a1) STARTUP prompt diff is minimal — additive fields + a
  read of tasks/ + a grep of task-request-map.jsonl. Total < 20 lines
  added to the STARTUP string.
</parameter>
