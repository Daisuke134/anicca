---
feature: dispatcher-live-dormant-mode
phase: 1b
mode: lean
generated_at: 2026-07-01
---

# Verification Architecture — dispatcher-live-dormant-mode

## Purity boundary

| Layer | Symbol | Side effects |
|---|---|---|
| PURE — `lib/quota_tracker.py` (append) | `has_realized_in_window(roi_rows, now_ts, window_days=90)` | none |
| PURE — `lib/quota_tracker.py` (append) | `compute_dormant_state(roi_rows, slot_age_days, time_horizon_days, now_ts)` — composes has_realized_in_window + is_dormant_with_horizon + count_consecutive_negative_windows | none |
| I/O — `lib/quota_tracker.py` (existing) | `write_dormant_sentinel(slot_dir, evidence)` — unchanged | disk write |
| ORCHESTRATOR — `proactive-loop-dispatch.py` STEP 3 | new inline check after existing recipe execution: read roi.jsonl → compute_dormant_state → maybe write_dormant_sentinel | 1 conditional, ~15 lines |

## Proof obligations

| PROP | Tier | Required | Maps to |
|---|---|---|---|
| PROP-L1-window-detection | 1 | true | REQ-L1 — realized>0 AND ts within window → True; else False |
| PROP-L2-live-mode-false-forces-not-dormant | 1 | true | REQ-L2 (live_mode False → is_dormant False unconditionally) |
| PROP-L2-live-mode-true-delegates-to-horizon-check | 1 | true | REQ-L2 (live_mode True → is_dormant follows is_dormant_with_horizon) |
| PROP-L3-window-count-uses-most-recent-first | 1 | true | REQ-L3 (count_consecutive_negative_windows called with correct ordering) |
| PROP-D1-dispatcher-invokes-check-when-roi-exists | 1 | true | REQ-D1 |
| PROP-D2-sentinel-written-only-when-dormant-and-not-exists | 1 | true | REQ-D2 idempotent |
| PROP-D3-never-removes-sentinel | 1 | true | grep dispatcher for `.dormant.sentinel` deletion = 0 |
| PROP-D4-exception-logged-and-continues | 1 | true | REQ-D4 fail-closed |
| PROP-E1-missing-roi-file | 1 | true | EDGE-E1 |
| PROP-E2-all-zero-realized | 1 | true | EDGE-E2 (this is where sprint-3 residual risk lived; live_mode=False saves us) |
| PROP-E3-old-realized-out-of-window | 1 | true | EDGE-E3 |
| PROP-E4-new-slot-not-dormant | 1 | true | EDGE-E4 |
| PROP-E6-malformed-roi-row-skipped | 1 | true | EDGE-E6 |
| PROP-I2-no-tmux-kill | 1 | true | REQ-I2 grep |

14 required:true. Tests:
- `__tests__/test_live_dormant_state.py` — PURE helpers unit tests
- `__tests__/test_dispatcher_dormant_integration.py` — dispatcher STEP 3 wiring

## Done = 4-D convergence

- spec ✓ test ✓ impl ✓ verification ✓
- vcsdd:vcsdd-adversary PASS (fresh context, 5 dims, 0 new findings)
- Live E2E: production gig currently has p-1782887987 realized=25000 from
  earlier sprint-4 (a2) test → live_mode=True on gig NOW. Kickstart dispatch
  → verify no sentinel written (slot too new for horizon, 30 mins age).
- Sanity: seed a synthetic-old slot with realized>0 old-window + neg
  windows → assert sentinel WOULD be written (test-only).
</parameter>
