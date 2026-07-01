---
feature: roi-writer-and-dormant
phase: 5
mode: lean
generated_at: 2026-07-01
---

# Purity Boundary Audit — roi-writer-and-dormant

## Declared Boundaries

| Layer | Symbol | Side effects |
|---|---|---|
| PURE — `lib/roi_track.py` | `compute_expected_jpy(picked)` | none (defensive int cast + clamp) |
| PURE — `lib/roi_track.py` | `roi_row(...)` | none (dict construction) |
| PURE — `lib/quota_tracker.py` (append) | `resolve_time_horizon_days(menu, default=14)` | none |
| PURE — `lib/quota_tracker.py` (append) | `is_dormant_with_horizon(...)` | none |
| I/O SINK — `lib/roi_track.py` | `append_roi_row(roi_jsonl_path, row)` | disk append (mode 0644) |
| ORCHESTRATOR — `proactive-loop-dispatch.py` | `_emit_roi_row(...)` helper called from 3 exit paths | composes PURE + I/O |

## Observed Boundaries

- `compute_expected_jpy` — 7 parametrized tests verify defensive behavior (None picked / missing fields / prob > 1 / prob < 0 / non-numeric); all pure dict input → int output.
- `roi_row` — deterministic dict build; JSON-serializable per test.
- `resolve_time_horizon_days` — 10 parametrized tests cover all fallback cases; no I/O.
- `is_dormant_with_horizon` — truth table + boundary strict-gt verified; no I/O; NOT called from dispatcher in sprint-3 (Group D deferred).
- `append_roi_row` — best-effort; returns {ok, status} dict; catches OSError; integration test with pre-created dir at roi.jsonl path proves IsADirectoryError caught.
- `_emit_roi_row` in dispatcher — thin wrapper around PURE compose + append; called from ALL 3 exit paths (verified by grep: 3 call sites + 1 def).

## Boundary Deviations

- `_emit_roi_row` writes core-status.json on write failure — this is the ORCHESTRATOR's declared I/O surface, not a purity violation.

## Summary

PURE layer verified side-effect-free. I/O sink confined to `<slot_dir>/roi.jsonl` (+ core-status.json failure log). No new dispatcher writes outside the declared paths per REQ-I1 mtime scoped test.

Sprint-4 will add `write_dormant_sentinel` back into the dispatcher call graph; sprint-3 keeps it out entirely per FIND-001 scope cut.
