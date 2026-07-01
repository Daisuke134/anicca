---
feature: recipe-6-actions
phase: 5
generated_at: 2026-07-01
mode: lean
---

# Verification Report — sprint-4 (d)

## Proof Obligations

| PROP | Status | Evidence |
|---|---|---|
| PROP-A1-kill_server-invokes-tmux | proved | test_A1_kill_server_invokes_tmux |
| PROP-A1-kill_server-timeout-caught | proved | test_A1_kill_server_timeout |
| PROP-A2-escalate-invokes-bot2bot | proved | test_A2_escalate_invokes_bot2bot |
| PROP-A2-escalate-missing-script-fail-soft | proved | test_A2_escalate_missing_script_fail_soft |
| PROP-A2-escalate-timeout-caught | proved | test_A2_escalate_timeout_caught |
| PROP-B1-send_keys-invokes-tmux-send-keys | proved | test_B1_send_keys_direct_keys |
| PROP-B1-send_keys-flow-variant-mapped | proved | test_B1_send_keys_flow_variant_mapped |
| PROP-B1-send_keys-unknown-flow-fail-soft | proved | test_B1_send_keys_unknown_flow_fail_soft |
| PROP-B1-send_keys-enter-flag-appends-Enter | proved | test_B1_send_keys_direct_keys (asserts Enter call) |
| PROP-B1-send_keys-timeout-caught | proved | test_B1_send_keys_timeout |
| PROP-C1-login-fail-soft-missing-script | proved | test_C1_login_missing_script_fail_soft |
| PROP-C1-login-timeout-caught | proved | test_C1_login_timeout |
| PROP-C2-npm_install-invokes-npm | proved | test_C2_npm_install_flow_consumed |
| PROP-C2-npm_install-flow-consumed | proved | test_C2_npm_install_flow_consumed + test_C2_npm_install_unknown_flow + test_C2_npm_install_missing_flow |
| PROP-C2-npm_install-timeout-caught | proved | test_C2_npm_install_timeout |
| PROP-C3-git_checkout-invokes-git | proved | test_C3_git_checkout_invokes_git + test_C3_git_checkout_missing_target_defaults |
| PROP-C3-git_checkout-timeout-caught | proved | test_C3_git_checkout_timeout |
| PROP-C-no-anicca-home-fail-soft | proved | test_group_C_empty_anicca_home_fail_soft |
| PROP-I1-no-restart-cmd-map-called | proved | test_I1_no_restart_cmd_map_called_from_non_restart_path |
| PROP-I2-never-raises | proved | test_I2_never_raises_ast_guard (AST walk of subprocess.run) |
| PROP-I3-no-slot-state-writes | proved | test_I3_no_slot_state_writes (grep) |
| PROP-I4-scaffold-set-empty-or-noop-only | proved | test_I4_scaffold_set_empty_or_noop_only + test_scaffold_deferred_actions_constant_is_noop_only |

## Summary

All 22 required obligations are `proved`. 503 tests total, all passing.
Regression baseline: PASS. 6 real subprocess wires added, each with
timeout + rc-check + fail-soft path. Signature change (anicca_home kwarg)
is backwards-compatible (default `""` triggers `-no-anicca-home-deferred`
across all Group-C wires).
