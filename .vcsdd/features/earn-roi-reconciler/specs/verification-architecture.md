---
feature: earn-roi-reconciler
phase: 1b
mode: lean
generated_at: 2026-07-01
---

# Verification Architecture — earn-roi-reconciler

## Purity boundary

| Layer | Symbol | Side effects |
|---|---|---|
| PURE — `lib/reconciler.py` (new) | `parse_settle_line(line: str) -> dict \| None` | none (str → dict\|None) |
| PURE — `lib/reconciler.py` | `should_update_realized(existing: int, new: int) -> bool` (REQ-R4 monotone gate) | none |
| PURE — `lib/reconciler.py` | `_ReconcileReport` dataclass | none |
| I/O — `lib/reconciler.py` | `reconcile(slot_dir: Path, now_ts: int) -> dict` | reads settle.jsonl + roi.jsonl; writes new roi.jsonl atomically; appends .unmatched.jsonl; writes state/reconciler-last-run.json + reconciler-offset.json |
| ORCHESTRATOR — `proactive-loop-dispatch.py` | STEP 6 hook: if picked.category == "reconciler", invoke reconcile directly in-process | composes |

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
| PROP-I2-writes-scoped | 1 | true | REQ-I2 (mtime snapshot of ~/gig/earnings.jsonl before/after) |
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
