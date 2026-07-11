# Verification Report — self-improve-checkpoint-resume (Phase 5)

mode: lean. 19/19 proof obligations from `specs/verification-architecture.md` proved by the
listed test, all re-executed live this session (`cd skills/earn/self-improve && source
~/.anicca-venvs/self-improve/bin/activate && python3 -m pytest tests/test_checkpoint_resume.py
tests/test_checkpoint_resume_wiring.py -v`) at commit `eba2270a`: **31/31 pass**.

| PROP | Discharged by | Result |
|---|---|---|
| PROP-CR1 | `test_prop_cr1_returns_none_for_nonexistent_runs_dir` | PROVED |
| PROP-CR1b | `test_prop_cr1b_relative_runs_dir_returns_absolute_path` | PROVED |
| PROP-CR2 | `test_prop_cr2_empty_runs_dir_returns_none`, `test_prop_cr2_runs_dir_with_only_current_run_id_returns_none` | PROVED |
| PROP-CR3 | `test_prop_cr3_selects_most_recent_run_by_name_not_highest_checkpoint_number` | PROVED |
| PROP-CR4 | `test_prop_cr4_integer_comparison_not_lexicographic` | PROVED |
| PROP-CR5 | `test_prop_cr5_run_without_checkpoints_subdirectory_is_skipped`, `test_prop_cr5_run_with_literally_empty_checkpoints_subdirectory_is_skipped` | PROVED |
| PROP-CR6 | `test_prop_cr6_ignores_non_matching_entries_interleaved_with_a_valid_one` | PROVED |
| PROP-CR7 | `test_prop_cr7_current_run_id_excluded_even_with_its_own_checkpoints` | PROVED |
| PROP-CR8 | `test_prop_cr8_selected_purely_by_name_empty_checkpoint_dir_never_inspected`, `test_prop_cr8_selected_purely_by_name_garbage_content_never_inspected` | PROVED |
| PROP-CR9 | `test_prop_cr9_pure_function_source_has_no_effectful_references_outside_main` | PROVED |
| PROP-CR10 | `test_prop_cr10_non_run_shaped_db_sibling_alone_returns_none`, `test_prop_cr10_non_run_shaped_db_sibling_ignored_when_a_real_run_also_present` | PROVED |
| PROP-CR11 | `test_prop_cr11_stray_file_only_checkpoints_dir_falls_through_to_older_run` | PROVED |
| PROP-CR12 | (a) `test_prop_cr12a_full_module_source_has_no_filesystem_mutation_api_references` (b) `test_prop_cr12b_module_never_imports_pathlib` (c) `test_prop_cr12c_no_mutation_across_a_none_returning_call`, `test_prop_cr12c_no_mutation_across_a_real_path_returning_call` | PROVED (all 3 sub-checks) |
| PROP-CR13 | `test_prop_cr13_resume_check_crash_falls_back_and_logs_distinct_message` | PROVED |
| PROP-CR14 | `test_prop_cr14_run_shaped_plain_file_falls_through_without_raising`, `test_prop_cr14_run_shaped_plain_file_only_returns_none` | PROVED |
| PROP-CR-WIRE1 | `test_prop_cr_wire1_pinned_checkpoint_resume_call_present_and_before_openevolve_invocation` | PROVED |
| PROP-CR-WIRE2 | `test_prop_cr_wire2_no_checkpoint_found_argument_list_unchanged_and_logged` (strengthened post-FIND-002 to assert exact argument count, not just substring absence) | PROVED |
| PROP-CR-WIRE2b | `test_prop_cr_wire2b_checkpoint_found_appends_single_checkpoint_flag` | PROVED |
| PROP-CR-WIRE3 | `test_prop_cr_wire3_exactly_one_checkpoint_resume_log_line_not_found_branch`, `test_prop_cr_wire3_exactly_one_checkpoint_resume_log_line_found_branch` | PROVED |
| PROP-CR-LIVE1 | `test_prop_cr_live1_end_to_end_two_run_fixture_selects_and_logs_checkpoint_20` (real `lib/checkpoint_resume.py`, real `sys.executable`, no stand-in for the pure logic) | PROVED |

Residual REQ-CR4 coverage: `test_req_cr4_runs_dir_with_only_non_run_shaped_entries_returns_none`.
Regression smoke: `test_regression_run_evolve_sh_remains_valid_bash_syntax` (`bash -n`) PASS.

## Full suite regression baseline

`python3 -m pytest tests/ -q` at commit `eba2270a`: **18 failed, 102 passed, 1 skipped**. All 18
failures confirmed pre-existing (unrelated `pm_backtest_strategy.py` test-fixture drift already
present on `main` HEAD, plus one worktree-path-only test that fails in ANY worktree checkout by
design — `test_ledger_reader.py::test_realized_summary_default_path_points_at_the_real_earn_ledger_location`
asserts a path ending in `anicca/skills/...` which is never true from `anicca/.worktrees/<name>/
skills/...`). Same 18 failure signatures confirmed on `main` HEAD via `cd ~/anicca/skills/earn/
self-improve && python3 -m pytest tests/ --ignore=tests/test_ledger_wallet_filter.py -q` (17 of
the 18 — `test_ledger_wallet_filter.py` itself was excluded from that comparison run because it
needs the `hypothesis` package, not installed in `~/.anicca-venvs/self-improve`, an unrelated
pre-existing environment gap). Zero new regressions introduced by this feature.

## Money-safety / scope discipline (adversary-verified, iteration 2)

`git diff main...feature/self-improve-checkpoint-resume` touches exactly: `skills/earn/self-improve/
lib/checkpoint_resume.py` (new), `skills/earn/self-improve/run_evolve.sh` (modified, one new
pre-invocation step), `skills/earn/self-improve/tests/test_checkpoint_resume.py` (new),
`skills/earn/self-improve/tests/test_checkpoint_resume_wiring.py` (new), plus this feature's own
`.vcsdd/features/self-improve-checkpoint-resume/**` bookkeeping. No reference to `strategies/
pm_backtest_strategy.py`, `promote_gate.sh`, `lib/promote_gate.py`, `lib/promote.py`,
`config.yaml`, `ai.anicca.self-improve-evolve.plist`, any wallet key, `.env`, or ledger file
anywhere in the diff (INV-CR2/INV-CR3 hold). This is a harness-only change to a paper/backtest
self-improvement loop; it never touches a live-money path.

## Bug caught and fixed during this session (Phase 3, iteration 1 -> 2)

Fresh Sonnet adversary FIND-001 (critical): `"${CHECKPOINT_ARGS[@]:-}"` on an empty bash array
under `set -u` expands to ONE stray empty-string argument on bash <4.4 (this Mac's default
`/bin/bash` is 3.2.57), not zero arguments — confirmed via a live `bash -c` repro
(`f() { echo "argc=$#"; }; arr=(); f "${arr[@]:-}"` -> `argc=1`). This would have broken
`openevolve-run`'s argparse (no catch-all positional, confirmed by reading the installed
`openevolve==0.3.0` CLI source) on the common "no prior checkpoint" path — i.e. nearly every
cycle until a checkpoint accumulates, worse than the stagnation bug this feature fixes. Corrected
to the canonical `"${CHECKPOINT_ARGS[@]+"${CHECKPOINT_ARGS[@]}"}"` idiom, confirmed live
(`argc=0` empty, `argc=2` populated). FIND-002 (test gap that let FIND-001 through) fixed by
strengthening `test_prop_cr_wire2_...` to assert exact argument count; confirmed this strengthened
test genuinely fails against the pre-fix code (9 args, trailing `""`) before confirming it passes
against the fix.
