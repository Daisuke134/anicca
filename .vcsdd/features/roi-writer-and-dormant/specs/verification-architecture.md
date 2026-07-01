---
feature: roi-writer-and-dormant
phase: 1b
mode: lean
generated_at: 2026-07-01
updated: iter-1 scope cut per FIND-001
---

# Verification Architecture — roi-writer-and-dormant (sprint-3 scope)

## Purity boundary

| Layer | Symbol | Side effects |
|---|---|---|
| PURE — `lib/roi_track.py` (new) | `roi_row(ts, pass_id, slot, budget, picked, outcome, realized, expected)` → dict | none |
| PURE — `lib/roi_track.py` | `compute_expected_jpy(picked)` → int | none (handles missing / OOB fields per EDGE-E6/E7) |
| PURE — `lib/quota_tracker.py` (append) | `resolve_time_horizon_days(menu, default=14)` → int | none |
| PURE — `lib/quota_tracker.py` (append) | `is_dormant_with_horizon(consecutive_neg_windows, slot_age_days, time_horizon_days)` → bool | none (PURE; NOT wired to dispatcher in sprint-3) |
| I/O SINK — `lib/roi_track.py` | `append_roi_row(roi_jsonl_path, row)` | disk append (mode 0644) |
| ORCHESTRATOR — `proactive-loop-dispatch.py` | STEP 7-post-append: build row → append → on failure log to core-status.json | composes; NEVER calls `is_dormant` or `write_dormant_sentinel` (REQ-I3) |

## Proof obligations

| PROP | Tier | Required | Maps to |
|---|---|---|---|
| PROP-W1-append-per-tick | 1 | true | REQ-W1, REQ-W5, EDGE-E1, EDGE-E8 |
| PROP-W2-shape | 1 | true | REQ-W2 (9-key schema, key names verbatim) |
| PROP-W3-expected-formula | 1 | true | REQ-W3, EDGE-E6, EDGE-E7 |
| PROP-W4-write-failure-no-crash | 1 | true | REQ-W4, EDGE-E2 (log + continue) |
| PROP-T1-horizon-fallback | 1 | true | REQ-T1, EDGE-E3, EDGE-E4 — parametrized: missing / None / 0 / -5 / "14"/ "abc" / valid |
| PROP-T2-is-dormant-with-horizon | 1 | true | REQ-T2 — truth table over both AND clauses (F/F, T/F, F/T, T/T) |
| PROP-I1-writes-scoped | 1 | true | REQ-I1 (mtime snapshot outside roi.jsonl + the pre-existing dispatcher writes) |
| PROP-I2-no-tmux-kill | 1 | true | REQ-I2 grep + AST — parses roi_track.py imports and asserts subprocess is used ONLY with argv lists that do not contain kill primitives |
| PROP-I3-no-legacy-dormant-in-dispatcher | 1 | true | REQ-I3 grep — `is_dormant\b` and `write_dormant_sentinel\b` = 0 hits in proactive-loop-dispatch.py |
| PROP-live-e2e-first-tick | 0 | false | Optional smoke test: run proactive-loop.sh gig; assert roi.jsonl gains exactly 1 row |

Lean mode required:true = 9. Tests:
- `__tests__/test_roi_track.py` — PURE + append (cross-platform)
- `__tests__/test_horizon_helpers.py` — resolve + is_dormant_with_horizon (cross-platform)
- `__tests__/test_dispatch_integration_roi.py` — integration on synthetic slot; also asserts core-status.json `step=7-roi-write-failed-*` log path via a permission-denied fixture

## Done = 4-D convergence

- spec ✓ test ✓ impl ✓ verification ✓
- adversary PASS + live `bash skills/_shared/proactive-loop.sh gig`; verify
  `~/loops/gig/roi.jsonl` grows by exactly one row per kickstart; existing
  rows byte-identical; `.dormant.sentinel` NOT created (per §1 scope-cut).

## Sprint-4 handoff notes (verifier requirement)

- Sprint-4 must add PROP-D* obligations for the sentinel wire.
- Sprint-4 must resolve the settle predicate (§7b INV-P2 rewrite) BEFORE
  wiring `is_dormant_with_horizon` to the dispatcher; otherwise the sentinel
  fires prematurely on any zero-realized run.
