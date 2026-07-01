---
feature: earn-roi-reconciler
phase: 1b
mode: lean
generated_at: 2026-07-01
---

# Verification Architecture — earn-roi-reconciler

## Purity boundary (FIND-004 fix — layered explicitly)

| Layer | Symbol | Side effects |
|---|---|---|
| PURE — `lib/reconciler.py` (new) | `parse_settle_line(line: str) -> dict \| None` | none (str → dict\|None) |
| PURE — `lib/reconciler.py` | `merge_realized(existing: int, new: int) -> tuple[int, str]` (REQ-R4 monotone-max; returns (new_value, status ∈ {"updated","skipped_dup","noop"})) | none |
| PURE — `lib/reconciler.py` | `_ReconcileReport` dataclass | none |
| I/O SINK 1 — `lib/reconciler.py` | `reconcile(slot_dir: Path, now_ts: int) -> dict` | reads settle.jsonl + roi.jsonl + .unmatched.jsonl tail; writes new roi.jsonl atomically; appends .unmatched.jsonl; writes state/reconciler-last-run.json + reconciler-offset.json IN THE ORDER SPECIFIED BY REQ-R5 |
| I/O SINK 2 (dispatcher patch) — `proactive-loop-dispatch.py` | STEP 6 branch: if `picked.get("category") == "reconciler"`, call reconcile(slot_dir, int(time.time())) in-process, skip enqueue_task_descriptor, record outcome — no other STEP 6 semantics change | composes; scope is 1 new branch (< 15 lines) inside STEP 6, tests exercise both branches |

**Scope clarification** (FIND-004): the dispatcher-branch patch is small
(1 conditional + 2 lines), lives inside this feature's spec, and is
verified by PROP-M2 (integration test). It does NOT justify a separate
VCSDD feature. If future work grows the dispatcher patch beyond ~30
lines, that becomes a new feature.

## Proof obligations

| PROP | Tier | Required | Maps to |
|---|---|---|---|
| PROP-R1-match-updates-roi | 1 | true | REQ-R1..R3 (single matched pair → roi row updated) |
| PROP-R1-mismatch-goes-to-unmatched | 1 | true | REQ-R7, EDGE-E6 |
| PROP-R4-monotone-no-decrease | 1 | true | REQ-R4 (existing > 0, new < existing → skipped_dup++, no write) |
| PROP-R5-atomic-write | 1 | true | REQ-R5 (crash between temp write and replace → old roi.jsonl intact) |
| PROP-R6-marker-written | 1 | true | REQ-R6 (state/reconciler-last-run.json contains report) |
| PROP-R7-unmatched-appends | 1 | true | REQ-R7 EDGE-E6 (verbatim + reason) |
| PROP-R8-offset-advances | 1 | true | REQ-R8 (second run reads only new rows) |
| PROP-R8-offset-reset-on-shrink | 1 | true | EDGE-E9 |
| PROP-E1-missing-settle-file | 1 | true | EDGE-E1 |
| PROP-E2-missing-roi-file | 1 | true | EDGE-E2 |
| PROP-E3-malformed-settle | 1 | true | EDGE-E3 |
| PROP-E5-dup-settle | 1 | true | EDGE-E5 |
| PROP-I1-no-tmux-kill | 1 | true | REQ-I1 static grep (reconciler.py) |
| PROP-I2-writes-scoped (FIND-006 fix) | 1 | true | REQ-I2 — 3-check test: (a) `os.stat` size AND (b) full-file SHA-256 hash of `~/gig/earnings.jsonl` are BYTE-IDENTICAL before/after; (c) grep the source of `lib/reconciler.py` for any string that starts with `~/gig` or `earnings.jsonl` used in a write-mode call — must be 0 write-mode hits. mtime is unreliable on some FS with 1s granularity or O_WRONLY-with-no-write and is NOT used as the sole predicate. |
| PROP-I3-no-human-touch | 1 | true | REQ-I3 grep |
| PROP-I4-no-shell-injection | 1 | true | REQ-I4 grep for shell=True / os.system |
| PROP-I5-no-fabricate | 1 | true | REQ-I5 (nonint jpy → realized=0, unmatched appends only, NEVER guesses) |
| PROP-M2-dispatcher-in-process | 1 | true | REQ-M2 (integration test: STEP 6 with reconciler item invokes reconcile in-process; no subprocess spawned; tasks/ descriptor has reconciler_report field) |
| PROP-M3-lowest-priority | 1 | true | REQ-M3 (pick_next with a normal ROI item + a cadence-elapsed reconciler item → normal item wins if its ROI > 0) |

19 required:true PROPs. Tests:
- `__tests__/test_reconciler.py` — PURE + I/O unit tests (cross-platform)
- `__tests__/test_reconciler_integration.py` — dispatcher STEP 6 integration + INV-4 scoped mtime snapshot (~/gig/earnings.jsonl untouched)

## Done = 4-D convergence

- spec ✓ test ✓ impl ✓ verification ✓
- vcsdd:vcsdd-adversary PASS (fresh context, 5 dims, 0 new findings)
- Live E2E: seed synthetic `settle.jsonl` into `~/loops/gig/` with a
  pass_id that already exists in the current `roi.jsonl`, run
  `python3 -c 'from lib.reconciler import reconcile; ...'`, verify the
  row's `roi_jpy_realized` becomes > 0, `state/reconciler-last-run.json`
  written, `~/gig/applied.jsonl` mtime unchanged.
