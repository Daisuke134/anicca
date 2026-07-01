---
feature: dispatcher-live-dormant-mode
phase: 5
generated_at: 2026-07-01
mode: lean
---

# Verification Report — sprint-4 (c)

## Proof Obligations

| PROP | Status | Evidence |
|---|---|---|
| PROP-L1-window-detection | proved | test_L1_recent_positive_returns_true + 4 sibling tests (test_live_dormant_state.py) |
| PROP-L2-live-mode-false-forces-not-dormant | proved | test_L2_live_mode_false_forces_not_dormant |
| PROP-L2-live-mode-true-delegates-to-horizon-check | proved | test_L2_live_mode_true_delegates_to_horizon_check |
| PROP-L3-window-count-uses-most-recent-LAST | proved | test_L3_rolling_7d_most_recent_last_ordering (verifies count>=1 with tail-negatives, out-of-window settle) |
| PROP-D1-dispatcher-invokes-check-when-roi-exists | proved | test_D1_dispatcher_invokes_dormant_check_when_roi_exists |
| PROP-D2-sentinel-written-only-when-dormant-and-not-exists | proved | test_D1_no_sentinel_when_no_realized + test_E5_sentinel_idempotent |
| PROP-D3-never-removes-sentinel | proved | test_D3_dispatcher_never_removes_sentinel (grep) |
| PROP-D4-exception-logged-and-continues | proved | test_D4_fail_closed_on_read_error |
| PROP-E1-missing-roi-file | proved | test_E1_empty_rows_live_mode_false_not_dormant |
| PROP-E2-all-zero-realized | proved | test_E2_all_zero_realized_live_mode_false |
| PROP-E3-old-realized-out-of-window | proved | test_E3_old_realized_out_of_window_live_mode_false |
| PROP-E4-new-slot-not-dormant | proved | test_E4_new_slot_not_dormant_despite_live_mode |
| PROP-E5-sentinel-idempotent | proved | test_E5_sentinel_idempotent |
| PROP-E6-malformed-roi-row-skipped | proved | test_E6_malformed_row_skipped |
| PROP-E7-missing-expected-treated-as-zero | proved | test_E7_missing_expected_treated_as_zero |
| PROP-L3-rolling-7d-most-recent-last | proved | test_L3_rolling_7d_most_recent_last_ordering |
| PROP-I2-no-tmux-kill | proved | test_I2_no_tmux_kill_referenced_in_dormant_wire (grep) |

## Summary

All 17 required obligations are `proved`. Total added surface: 2 PURE helpers
in quota_tracker.py + 1 guarded try/except block (~35 lines) in the dispatcher.
480 tests total (was 460 + 20 new, 1 legacy adjusted). Regression baseline: PASS.
Live E2E deferred to Phase 6 convergence step.
