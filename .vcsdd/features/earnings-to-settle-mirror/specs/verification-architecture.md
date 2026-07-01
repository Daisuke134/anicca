---
feature: earnings-to-settle-mirror
phase: 1b
mode: lean
generated_at: 2026-07-01
---

# Verification Architecture — earnings-to-settle-mirror

## Purity boundary

| Layer | Symbol | Side effects |
|---|---|---|
| PURE — `lib/settle_mirror.py` | `parse_earnings_line(line: str) -> dict \| None` | none |
| PURE — `lib/settle_mirror.py` | `is_settled_row(row: dict) -> bool` (checks status in SETTLED set + jpy > 0) | none |
| PURE — `lib/settle_mirror.py` | `lookup_pass_id_in_tasks(requestId: str, tasks_dir: Path) -> str \| None` (returns pass_id if any tasks/*.json has picked.name or picked.category containing requestId) | reads tasks_dir (I/O but read-only-scoped) |
| PURE — `lib/settle_mirror.py` | `lookup_pass_id_in_roi(requestId: str, roi_path: Path) -> str \| None` (returns pass_id if any roi.jsonl row's outcome contains requestId) | reads roi.jsonl (I/O but read-only) |
| PURE — `lib/settle_mirror.py` | `build_settle_row(request_id, jpy, pass_id, now_ts, slot, earnings_status, earnings_ts) -> dict` | none |
| I/O SINK — `lib/settle_mirror.py` | `mirror_earnings_to_settle(slot_dir, earnings_path, now_ts) -> dict` | reads earnings.jsonl + settle.jsonl tail (dedup); writes settle.jsonl (append) + state/settle-mirror-last-run.json + state/settle-mirror-offset.json |
| ORCHESTRATOR — `proactive-loop-dispatch.py` STEP 6 branch | new elif for `picked.category == "settle-mirror"` — invoke in-process, skip enqueue | ~10 lines |

## Proof obligations

| PROP | Tier | Required | Maps to |
|---|---|---|---|
| PROP-R1-invoke-and-append | 1 | true | REQ-R1, REQ-R3 (settled row → new settle.jsonl row) |
| PROP-R3-pass-id-from-tasks | 1 | true | REQ-R3(ii), EDGE-E6, EDGE-E9 (tasks/ match wins) |
| PROP-R3-pass-id-from-roi | 1 | true | REQ-R3(ii) fallback |
| PROP-R4-unmatched-fallback | 1 | true | REQ-R4 (no lookup → unmatched-requestId-<x> sentinel; reconciler will route this to unmatched.jsonl) |
| PROP-R5-dedup | 1 | true | REQ-R5, EDGE-E5 |
| PROP-R6-atomic-offset-last | 1 | true | REQ-R6 (v) |
| PROP-E3-non-settled-ignored | 1 | true | EDGE-E3 (applied / delivered status not settled) |
| PROP-E4-zero-jpy-ignored | 1 | true | EDGE-E4 |
| PROP-E8-offset-reset-shrink | 1 | true | EDGE-E8 |
| PROP-M2-dispatcher-invokes-in-process | 1 | true | REQ-M2 (integration test: reconciler-category-style hook fires, tasks/ untouched, build_log outcome starts with "settle-mirror:new=") |
| PROP-I2-no-gig-write | 1 | true | REQ-I2 (SHA-256 of earnings.jsonl before/after + source grep for write-mode ~/gig ref = 0 hits) |
| PROP-I3-no-human-touch | 1 | true | REQ-I3 grep |
| PROP-I4-no-shell-injection | 1 | true | REQ-I4 grep |
| PROP-I5-no-fabricate-pass-id | 1 | true | REQ-I5 (mock scan returning None → settle row's pass_id starts with "unmatched-requestId-") |
| PROP-integration-full-loop | 1 | true | E2E: seed earnings.jsonl with a 検収 row referencing a requestId that matches a real task descriptor; invoke mirror; assert settle.jsonl row created with matched pass_id; then invoke reconciler; assert roi.jsonl updated. Full pipeline. |

15 required:true. Tests:
- `__tests__/test_settle_mirror.py` — PURE + I/O unit tests
- `__tests__/test_settle_mirror_integration.py` — dispatcher branch + full pipeline (earnings → mirror → settle → reconcile → roi)

## Done = 4-D convergence

- spec ✓ test ✓ impl ✓ verification ✓
- vcsdd:vcsdd-adversary PASS (fresh context, 5 dims, 0 new findings)
- Live E2E: seed a synthetic earnings row referencing a real gig requestId
  matching a real tasks/*.json descriptor; run mirror; verify settle.jsonl
  gains the row with the real pass_id; then run reconciler; verify
  roi.jsonl updated; then verify ~/gig/earnings.jsonl SHA-256 unchanged.
</parameter>
