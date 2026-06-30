---
feature: gig-run-shim
phase: 5
mode: lean
generated_at: 2026-07-01
---

# Verification Report — gig-run-shim

## Proof Obligations

Lean; 11 required:true (Tier 0/1). All proved via test harness.

| PROP | Tier | Status |
|------|------|--------|
| PROP-S1-back-compat | 1 | proved (test_status_json_back_compat_and_shim_observability: EXISTING_KEYS XOR check) |
| PROP-S2-shape | 1 | proved (test_returns_4_named_keys + integration shape assert) |
| PROP-S3-installed-both-checks | 1 | proved (test_installed_requires_both_disk_and_rc_zero — Case A/B/C) |
| PROP-S4-core-status-read | 1 | proved (test_last_pass_ts_and_step_from_core_status) |
| PROP-S5-pass-count | 1 | proved (test_build_log_passes_counts_headers + test_build_log_empty_returns_zero + integration sentinel sanity) |
| PROP-I1-no-loops-writes | 1 | proved (sentinel-seeded mtime snapshot + content invariance + file-set XOR) |
| PROP-I2-no-tmux-kill | 1 | proved (test_no_tmux_kill_in_run_sh static grep) |
| PROP-I3-pre-migration-graceful | 1 | proved (test_pre_migration_no_loops_dir) |
| PROP-D1-no-human-touch | 1 | proved (test_no_human_touch parametrized over both sources) |
| PROP-E2-malformed-json-no-crash | 1 | proved (test_malformed_core_status_no_crash) |
| PROP-E5-disk-but-not-loaded | 1 | proved (test_installed_requires_both_disk_and_rc_zero Case B) |

## Summary

Trajectory:
- Phase 1c spec gate: 0 findings (PASS @ iter-1)
- Phase 2a RED: 3 modules canonical fail-on-import (ModuleNotFoundError lib.proactive_observe)
- Phase 2b GREEN: 287/287 (= 275 + 11 new + 1 sentinel-fix)
- Phase 2c REFACTOR: still 287
- Phase 3: 1 → 0 (2 iters; FIND-001 mtime-snapshot no-op fixed)
- Phase 5: this report + security + purity audit

Live E2E:
- bash skills/earn/gig/run.sh → JSON with 10 existing keys + proactive_loop object
- 23 production in-flight Coconala apps observed (= LAYER C tmux core alive)
- ~/loops/gig/ mtimes UNCHANGED across the call (= INV-4 honored)

All 11 required:true PROPs reach `proved`.
