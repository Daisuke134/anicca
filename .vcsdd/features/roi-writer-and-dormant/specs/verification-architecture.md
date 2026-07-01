---
feature: roi-writer-and-dormant
phase: 1b
mode: lean
generated_at: 2026-07-01
---

# Verification Architecture — roi-writer-and-dormant

## Purity boundary

| Layer | Symbol | Side effects |
|---|---|---|
| PURE — `lib/roi_track.py` (new) | `roi_row(pass_id, ts, slot, budget, picked, outcome, realized=0, expected=0)` | none |
| PURE — `lib/roi_track.py` | `bucket_by_day(rows, now_ts)` — group roi rows into 24h windows | none |
| PURE — `lib/roi_track.py` | `sum_realized_per_window(windowed)` — list[int] most recent first | none |
| PURE — `lib/roi_track.py` | `resolve_time_horizon_days(menu, default=14)` | none |
| PURE — `lib/quota_tracker.py` (add) | `is_dormant_with_horizon(consecutive_neg_windows, slot_age_days, time_horizon_days)` | none |
| I/O SINK — `lib/roi_track.py` | `append_roi_row(slot_dir, row)` | disk append |
| I/O — `lib/quota_tracker.py` (existing) | `write_dormant_sentinel(slot_dir, evidence)` | disk write |
| ORCHESTRATOR — `proactive-loop-dispatch.py` | STEP 7-post: build row → append → compute dormant → maybe sentinel | composes |

## Proof obligations

| PROP | Tier | Required | Maps to |
|---|---|---|---|
| PROP-W1-append-per-tick | 1 | true | REQ-W1, REQ-W5 (row appended, existing rows preserved) |
| PROP-W2-shape | 1 | true | REQ-W2 (9-key schema) |
| PROP-W3-expected-formula | 1 | true | REQ-W3 (roi × prob when picked, 0 else) |
| PROP-W4-write-failure-no-crash | 1 | true | REQ-W4, EDGE-E2 |
| PROP-D1-uses-menu-horizon | 1 | true | REQ-D1, REQ-T1 |
| PROP-D2-windowing | 1 | true | REQ-D2 (bucket by day, count consecutive negatives) |
| PROP-D3-age-guard | 1 | true | REQ-D3, EDGE-E5 (new slot never dormant) |
| PROP-D4-sentinel-write | 1 | true | REQ-D4, EDGE-E6 (idempotent) |
| PROP-D5-no-sentinel-removal | 1 | true | REQ-D5 static grep — no `unlink(.dormant.sentinel)` |
| PROP-T1-horizon-fallback | 1 | true | REQ-T1, EDGE-E3, EDGE-E4 |
| PROP-T2-is-dormant-with-horizon | 1 | true | REQ-T2 (both AND clauses required) |
| PROP-I1-writes-scoped | 1 | true | REQ-I1 mtime snapshot outside roi.jsonl + .dormant.sentinel |
| PROP-I2-no-tmux-kill | 1 | true | REQ-I2 static grep |
| PROP-I3-uses-horizon-not-7 | 1 | true | REQ-I3 grep — dispatcher calls is_dormant_with_horizon, NOT is_dormant |
| PROP-E7-partial-window | 1 | true | EDGE-E7 (< 2×horizon days → not dormant) |

15 required:true. Tests:
- `__tests__/test_roi_track.py` — PURE + append unit tests
- `__tests__/test_is_dormant_with_horizon.py` — PURE dormant math
- `__tests__/test_dispatch_integration_roi.py` — integration on synthetic slot

## Done = 4-D convergence

- spec ✓ test ✓ impl ✓ verification ✓
- adversary PASS + live `bash skills/_shared/proactive-loop.sh gig` after
  wire; verify `~/loops/gig/roi.jsonl` gains a row per tick, existing rows
  preserved, `.dormant.sentinel` NOT written (= slot too young + healthy
  gig has 23 in-flight apps).
