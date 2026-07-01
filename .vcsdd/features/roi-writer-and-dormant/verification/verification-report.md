---
feature: roi-writer-and-dormant
phase: 5
mode: lean
generated_at: 2026-07-01
---

# Verification Report — roi-writer-and-dormant

## Proof Obligations

Lean; 9 required:true PROPs. All proved via test harness.

| PROP | Status |
|------|--------|
| PROP-W1-append-per-tick | proved (test_dispatch_appends_exactly_one_roi_row + test_dispatch_emits_roi_on_skip_dormant_sentinel + test_dispatch_emits_roi_on_picked_none_sink) — every exit path emits |
| PROP-W2-shape | proved (test_all_9_keys_present + integration shape assert) |
| PROP-W3-expected-formula | proved (7 unit tests: basic × / None picked / missing fields / prob clamp / non-numeric) |
| PROP-W4-write-failure-no-crash | proved (test_write_failure_returns_error_dict + integration test_dispatch_logs_roi_write_failure_and_continues via pre-created dir → IsADirectoryError) |
| PROP-T1-horizon-fallback | proved (10 parametrized cases: missing / None / 0 / -5 / str / non-cast) |
| PROP-T2-is-dormant-with-horizon | proved (truth table F/F, T/F, F/T, T/T + boundary strict-gt + FAST/SLOW class cases) |
| PROP-I1-writes-scoped | proved (test_dispatch_roi_write_does_not_touch_unrelated_files scoped mtime snapshot) |
| PROP-I2-no-tmux-kill | proved (test_dispatcher_ast_no_kill_argv AST walk over literals) |
| PROP-I3-no-legacy-dormant-in-dispatcher | proved (test_dispatcher_does_not_call_legacy_dormant_symbols \b regex) |

Optional PROP-live-e2e-first-tick: satisfied (production gig kickstart delta=1 exact, expected=16000 exact).

## Summary

VCSDD trajectory:
- Phase 1c spec: 6→0 (2 iter; 1 critical dead-code Group D scope-cut to sprint-4)
- Phase 2a RED: 3 modules canonical
- Phase 2b GREEN: 328 → 365 → 369 (+41 net across 2 cycles)
- Phase 3: 3→0 (2 iter; 1 critical REQ-W1 exit-path bug caught + fixed)
- Phase 5: this + security + purity + grep

Live production proof:
- Kickstart 1: roi.jsonl created 259B, row=follow-up-warm-leads expected=16000
- Kickstart 2 (post FIND-001 fix): rows 2 → 3 (delta=1 exact per REQ-W1)
- .dormant.sentinel ABSENT throughout (Group D deferred to sprint-4 correctly)
- ~/gig/ ledger mtime UNCHANGED (INV-4)
- gig-cli.sh --status: ALIVE (INV-1, INV-P1)

Sprint-4 carry (documented in behavioral-spec.md §6):
- LAYER C settle callback wire → roi_jpy_realized real values
- Redefine "negative window" per §7b INV-P2 (settled vs expected, not raw sum<0)
- Wire is_dormant_with_horizon to dispatcher AFTER settle wire lands
- .slot-created.ts sentinel for cross-platform slot_age_days
- 24h window boundary decision (midnight-UTC vs local vs strict-24h)
