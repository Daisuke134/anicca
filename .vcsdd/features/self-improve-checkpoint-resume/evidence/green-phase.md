green-phase: GREEN — all 31 new tests pass, 0 regressions

=== 31 new tests (test_checkpoint_resume.py + test_checkpoint_resume_wiring.py) ===
============================= test session starts ==============================
platform darwin -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0 -- /Users/anicca/.anicca-venvs/self-improve/bin/python3
cachedir: .pytest_cache
rootdir: /Users/anicca/anicca/.worktrees/self-improve-checkpoint-resume/skills/earn/self-improve
plugins: anyio-4.14.1
collecting ... collected 31 items

tests/test_checkpoint_resume.py::test_prop_cr1_returns_none_for_nonexistent_runs_dir PASSED [  3%]
tests/test_checkpoint_resume.py::test_prop_cr1b_relative_runs_dir_returns_absolute_path PASSED [  6%]
tests/test_checkpoint_resume.py::test_prop_cr2_empty_runs_dir_returns_none PASSED [  9%]
tests/test_checkpoint_resume.py::test_prop_cr2_runs_dir_with_only_current_run_id_returns_none PASSED [ 12%]
tests/test_checkpoint_resume.py::test_prop_cr3_selects_most_recent_run_by_name_not_highest_checkpoint_number PASSED [ 16%]
tests/test_checkpoint_resume.py::test_prop_cr4_integer_comparison_not_lexicographic PASSED [ 19%]
tests/test_checkpoint_resume.py::test_prop_cr5_run_without_checkpoints_subdirectory_is_skipped PASSED [ 22%]
tests/test_checkpoint_resume.py::test_prop_cr5_run_with_literally_empty_checkpoints_subdirectory_is_skipped PASSED [ 25%]
tests/test_checkpoint_resume.py::test_prop_cr6_ignores_non_matching_entries_interleaved_with_a_valid_one PASSED [ 29%]
tests/test_checkpoint_resume.py::test_prop_cr7_current_run_id_excluded_even_with_its_own_checkpoints PASSED [ 32%]
tests/test_checkpoint_resume.py::test_prop_cr8_selected_purely_by_name_empty_checkpoint_dir_never_inspected PASSED [ 35%]
tests/test_checkpoint_resume.py::test_prop_cr8_selected_purely_by_name_garbage_content_never_inspected PASSED [ 38%]
tests/test_checkpoint_resume.py::test_prop_cr9_pure_function_source_has_no_effectful_references_outside_main PASSED [ 41%]
tests/test_checkpoint_resume.py::test_prop_cr10_non_run_shaped_db_sibling_alone_returns_none PASSED [ 45%]
tests/test_checkpoint_resume.py::test_prop_cr10_non_run_shaped_db_sibling_ignored_when_a_real_run_also_present PASSED [ 48%]
tests/test_checkpoint_resume.py::test_prop_cr11_stray_file_only_checkpoints_dir_falls_through_to_older_run PASSED [ 51%]
tests/test_checkpoint_resume.py::test_prop_cr14_run_shaped_plain_file_falls_through_without_raising PASSED [ 54%]
tests/test_checkpoint_resume.py::test_prop_cr14_run_shaped_plain_file_only_returns_none PASSED [ 58%]
tests/test_checkpoint_resume.py::test_prop_cr12a_full_module_source_has_no_filesystem_mutation_api_references PASSED [ 61%]
tests/test_checkpoint_resume.py::test_prop_cr12b_module_never_imports_pathlib PASSED [ 64%]
tests/test_checkpoint_resume.py::test_prop_cr12c_no_mutation_across_a_none_returning_call PASSED [ 67%]
tests/test_checkpoint_resume.py::test_prop_cr12c_no_mutation_across_a_real_path_returning_call PASSED [ 70%]
tests/test_checkpoint_resume.py::test_req_cr4_runs_dir_with_only_non_run_shaped_entries_returns_none PASSED [ 74%]
tests/test_checkpoint_resume_wiring.py::test_prop_cr_wire1_pinned_checkpoint_resume_call_present_and_before_openevolve_invocation PASSED [ 77%]
tests/test_checkpoint_resume_wiring.py::test_prop_cr_wire2_no_checkpoint_found_argument_list_unchanged_and_logged PASSED [ 80%]
tests/test_checkpoint_resume_wiring.py::test_prop_cr_wire2b_checkpoint_found_appends_single_checkpoint_flag PASSED [ 83%]
tests/test_checkpoint_resume_wiring.py::test_prop_cr_wire3_exactly_one_checkpoint_resume_log_line_not_found_branch PASSED [ 87%]
tests/test_checkpoint_resume_wiring.py::test_prop_cr_wire3_exactly_one_checkpoint_resume_log_line_found_branch PASSED [ 90%]
tests/test_checkpoint_resume_wiring.py::test_prop_cr13_resume_check_crash_falls_back_and_logs_distinct_message PASSED [ 93%]
tests/test_checkpoint_resume_wiring.py::test_prop_cr_live1_end_to_end_two_run_fixture_selects_and_logs_checkpoint_20 PASSED [ 96%]
tests/test_checkpoint_resume_wiring.py::test_regression_run_evolve_sh_remains_valid_bash_syntax PASSED [100%]

============================== 31 passed in 1.55s ==============================

=== full suite regression check (tests/) ===
FFFFFFFFFF..................................F.......FF.............F.... [ 60%]
..................FF.....................FF.....                         [100%]
=================================== FAILURES ===================================
_____________ test_good_candidate_is_eligible_for_adversary_review _____________

tmp_path = PosixPath('/private/var/folders/c1/11fd4j597vx4fb8tnv25y28r0000gn/T/pytest-of-anicca/pytest-18/test_good_candidate_is_eligibl0')

    def test_good_candidate_is_eligible_for_adversary_review(tmp_path):
>       _, candidate_path = _good_candidate(tmp_path)
                            ^^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_adversary_disapprove.py:47: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/test_adversary_disapprove.py:26: in _good_candidate
    code = patched_baseline_code(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

replacements = (('config.get("edge_weight", 0.25)', 'config.get("edge_weight", 0.4)'), ('config.get("conf_weight", 0.45)', 'config.get("conf_weight", 0.1)'))

    def patched_baseline_code(*replacements: tuple) -> str:
        """Apply a sequence of (old, new) `str.replace(old, new, 1)` edits to the real baseline
        program text. Asserts every replacement actually matched something in the current baseline
        file, so a typo'd test literal fails loudly instead of silently producing a byte-identical
        "candidate" that trivially passes scope_guard for the wrong reason."""
        code = read_baseline_code()
        for old, new in replacements:
>           assert old in code, f"expected baseline text not found (test fixture drifted?): {old!r}"
E           AssertionError: expected baseline text not found (test fixture drifted?): 'config.get("edge_weight", 0.25)'
E           assert 'config.get("edge_weight", 0.25)' in '"""pm_backtest_strategy.py — the self-contained, deterministic, backtestable openevolve program\nthis feature evolves...ost_usd": cost_usd, "net_usd": net, "n_trades": n_trades}\n\n\nif __name__ == "__main__":\n    print(run_backtest())\n'

tests/conftest.py:37: AssertionError
__ test_adversary_fail_blocks_promotion_even_though_deterministic_gates_pass ___

tmp_path = PosixPath('/private/var/folders/c1/11fd4j597vx4fb8tnv25y28r0000gn/T/pytest-of-anicca/pytest-18/test_adversary_fail_blocks_pro0')

    def test_adversary_fail_blocks_promotion_even_though_deterministic_gates_pass(tmp_path):
>       candidate_code, candidate_path = _good_candidate(tmp_path)
                                         ^^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_adversary_disapprove.py:59: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/test_adversary_disapprove.py:26: in _good_candidate
    code = patched_baseline_code(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

replacements = (('config.get("edge_weight", 0.25)', 'config.get("edge_weight", 0.4)'), ('config.get("conf_weight", 0.45)', 'config.get("conf_weight", 0.1)'))

    def patched_baseline_code(*replacements: tuple) -> str:
        """Apply a sequence of (old, new) `str.replace(old, new, 1)` edits to the real baseline
        program text. Asserts every replacement actually matched something in the current baseline
        file, so a typo'd test literal fails loudly instead of silently producing a byte-identical
        "candidate" that trivially passes scope_guard for the wrong reason."""
        code = read_baseline_code()
        for old, new in replacements:
>           assert old in code, f"expected baseline text not found (test fixture drifted?): {old!r}"
E           AssertionError: expected baseline text not found (test fixture drifted?): 'config.get("edge_weight", 0.25)'
E           assert 'config.get("edge_weight", 0.25)' in '"""pm_backtest_strategy.py — the self-contained, deterministic, backtestable openevolve program\nthis feature evolves...ost_usd": cost_usd, "net_usd": net, "n_trades": n_trades}\n\n\nif __name__ == "__main__":\n    print(run_backtest())\n'

tests/conftest.py:37: AssertionError
_ test_adversary_missing_or_erroring_verdict_also_blocks_promotion_fail_closed _

tmp_path = PosixPath('/private/var/folders/c1/11fd4j597vx4fb8tnv25y28r0000gn/T/pytest-of-anicca/pytest-18/test_adversary_missing_or_erro0')

    def test_adversary_missing_or_erroring_verdict_also_blocks_promotion_fail_closed(tmp_path):
        """EDGE-3: the adversary being unavailable/erroring must BLOCK promotion, never silently skip
        the check (fail-closed), even though the deterministic gates passed."""
>       candidate_code, candidate_path = _good_candidate(tmp_path)
                                         ^^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_adversary_disapprove.py:80: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/test_adversary_disapprove.py:26: in _good_candidate
    code = patched_baseline_code(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

replacements = (('config.get("edge_weight", 0.25)', 'config.get("edge_weight", 0.4)'), ('config.get("conf_weight", 0.45)', 'config.get("conf_weight", 0.1)'))

    def patched_baseline_code(*replacements: tuple) -> str:
        """Apply a sequence of (old, new) `str.replace(old, new, 1)` edits to the real baseline
        program text. Asserts every replacement actually matched something in the current baseline
        file, so a typo'd test literal fails loudly instead of silently producing a byte-identical
        "candidate" that trivially passes scope_guard for the wrong reason."""
        code = read_baseline_code()
        for old, new in replacements:
>           assert old in code, f"expected baseline text not found (test fixture drifted?): {old!r}"
E           AssertionError: expected baseline text not found (test fixture drifted?): 'config.get("edge_weight", 0.25)'
E           assert 'config.get("edge_weight", 0.25)' in '"""pm_backtest_strategy.py — the self-contained, deterministic, backtestable openevolve program\nthis feature evolves...ost_usd": cost_usd, "net_usd": net, "n_trades": n_trades}\n\n\nif __name__ == "__main__":\n    print(run_backtest())\n'

tests/conftest.py:37: AssertionError
_ test_adversary_pass_on_eligible_candidate_promotes_and_calls_promote_exactly_once _

tmp_path = PosixPath('/private/var/folders/c1/11fd4j597vx4fb8tnv25y28r0000gn/T/pytest-of-anicca/pytest-18/test_adversary_pass_on_eligibl0')

    def test_adversary_pass_on_eligible_candidate_promotes_and_calls_promote_exactly_once(tmp_path):
>       candidate_code, candidate_path = _good_candidate(tmp_path)
                                         ^^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_adversary_disapprove.py:94: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/test_adversary_disapprove.py:26: in _good_candidate
    code = patched_baseline_code(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

replacements = (('config.get("edge_weight", 0.25)', 'config.get("edge_weight", 0.4)'), ('config.get("conf_weight", 0.45)', 'config.get("conf_weight", 0.1)'))

    def patched_baseline_code(*replacements: tuple) -> str:
        """Apply a sequence of (old, new) `str.replace(old, new, 1)` edits to the real baseline
        program text. Asserts every replacement actually matched something in the current baseline
        file, so a typo'd test literal fails loudly instead of silently producing a byte-identical
        "candidate" that trivially passes scope_guard for the wrong reason."""
        code = read_baseline_code()
        for old, new in replacements:
>           assert old in code, f"expected baseline text not found (test fixture drifted?): {old!r}"
E           AssertionError: expected baseline text not found (test fixture drifted?): 'config.get("edge_weight", 0.25)'
E           assert 'config.get("edge_weight", 0.25)' in '"""pm_backtest_strategy.py — the self-contained, deterministic, backtestable openevolve program\nthis feature evolves...ost_usd": cost_usd, "net_usd": net, "n_trades": n_trades}\n\n\nif __name__ == "__main__":\n    print(run_backtest())\n'

tests/conftest.py:37: AssertionError
_ test_ineligible_regressing_candidate_never_becomes_eligible_for_adversary_review _

tmp_path = PosixPath('/private/var/folders/c1/11fd4j597vx4fb8tnv25y28r0000gn/T/pytest-of-anicca/pytest-18/test_ineligible_regressing_can0')

    def test_ineligible_regressing_candidate_never_becomes_eligible_for_adversary_review(tmp_path):
        """A candidate that already fails a deterministic gate (the same loose-threshold regressing
        candidate from test_heldout_regress.py) must never even be marked eligible for adversary
        review — this is the flag `promote_gate.sh`'s real shell wrapper uses to skip the (costly)
        LLM call entirely, not just skip promotion after asking."""
>       _, candidate_path = _regressing_candidate(tmp_path)
                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_adversary_disapprove.py:118: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/test_adversary_disapprove.py:36: in _regressing_candidate
    code = patched_baseline_code(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

replacements = (('config.get("min_edge", 0.18)', 'config.get("min_edge", 0.01)'), ('config.get("min_confidence", 7.0)', 'config.get("...ce", 0.85)', 'config.get("max_price", 1.0)'), ('config.get("min_liquidity", 0.4)', 'config.get("min_liquidity", 0.0)'))

    def patched_baseline_code(*replacements: tuple) -> str:
        """Apply a sequence of (old, new) `str.replace(old, new, 1)` edits to the real baseline
        program text. Asserts every replacement actually matched something in the current baseline
        file, so a typo'd test literal fails loudly instead of silently producing a byte-identical
        "candidate" that trivially passes scope_guard for the wrong reason."""
        code = read_baseline_code()
        for old, new in replacements:
>           assert old in code, f"expected baseline text not found (test fixture drifted?): {old!r}"
E           AssertionError: expected baseline text not found (test fixture drifted?): 'config.get("min_edge", 0.18)'
E           assert 'config.get("min_edge", 0.18)' in '"""pm_backtest_strategy.py — the self-contained, deterministic, backtestable openevolve program\nthis feature evolves...ost_usd": cost_usd, "net_usd": net, "n_trades": n_trades}\n\n\nif __name__ == "__main__":\n    print(run_backtest())\n'

tests/conftest.py:37: AssertionError
___________________ test_better_candidate_scope_guard_passes ___________________

    def test_better_candidate_scope_guard_passes():
        baseline_code = read_baseline_code()
>       candidate_code = _better_candidate_code()
                         ^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_baseline_beat.py:51: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/test_baseline_beat.py:43: in _better_candidate_code
    return patched_baseline_code(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

replacements = (('config.get("edge_weight", 0.25)', 'config.get("edge_weight", 0.4)'), ('config.get("conf_weight", 0.45)', 'config.get("conf_weight", 0.1)'))

    def patched_baseline_code(*replacements: tuple) -> str:
        """Apply a sequence of (old, new) `str.replace(old, new, 1)` edits to the real baseline
        program text. Asserts every replacement actually matched something in the current baseline
        file, so a typo'd test literal fails loudly instead of silently producing a byte-identical
        "candidate" that trivially passes scope_guard for the wrong reason."""
        code = read_baseline_code()
        for old, new in replacements:
>           assert old in code, f"expected baseline text not found (test fixture drifted?): {old!r}"
E           AssertionError: expected baseline text not found (test fixture drifted?): 'config.get("edge_weight", 0.25)'
E           assert 'config.get("edge_weight", 0.25)' in '"""pm_backtest_strategy.py — the self-contained, deterministic, backtestable openevolve program\nthis feature evolves...ost_usd": cost_usd, "net_usd": net, "n_trades": n_trades}\n\n\nif __name__ == "__main__":\n    print(run_backtest())\n'

tests/conftest.py:37: AssertionError
_________ test_better_candidate_beats_baseline_on_stage2_walk_forward __________

tmp_path = PosixPath('/private/var/folders/c1/11fd4j597vx4fb8tnv25y28r0000gn/T/pytest-of-anicca/pytest-18/test_better_candidate_beats_ba0')

    def test_better_candidate_beats_baseline_on_stage2_walk_forward(tmp_path):
>       candidate_code = _better_candidate_code()
                         ^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_baseline_beat.py:60: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/test_baseline_beat.py:43: in _better_candidate_code
    return patched_baseline_code(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

replacements = (('config.get("edge_weight", 0.25)', 'config.get("edge_weight", 0.4)'), ('config.get("conf_weight", 0.45)', 'config.get("conf_weight", 0.1)'))

    def patched_baseline_code(*replacements: tuple) -> str:
        """Apply a sequence of (old, new) `str.replace(old, new, 1)` edits to the real baseline
        program text. Asserts every replacement actually matched something in the current baseline
        file, so a typo'd test literal fails loudly instead of silently producing a byte-identical
        "candidate" that trivially passes scope_guard for the wrong reason."""
        code = read_baseline_code()
        for old, new in replacements:
>           assert old in code, f"expected baseline text not found (test fixture drifted?): {old!r}"
E           AssertionError: expected baseline text not found (test fixture drifted?): 'config.get("edge_weight", 0.25)'
E           assert 'config.get("edge_weight", 0.25)' in '"""pm_backtest_strategy.py — the self-contained, deterministic, backtestable openevolve program\nthis feature evolves...ost_usd": cost_usd, "net_usd": net, "n_trades": n_trades}\n\n\nif __name__ == "__main__":\n    print(run_backtest())\n'

tests/conftest.py:37: AssertionError
___________ test_better_candidate_has_non_negative_worst_window_oos ____________

tmp_path = PosixPath('/private/var/folders/c1/11fd4j597vx4fb8tnv25y28r0000gn/T/pytest-of-anicca/pytest-18/test_better_candidate_has_non_0')

    def test_better_candidate_has_non_negative_worst_window_oos(tmp_path):
        """Strengthens the beats-baseline claim above: the improvement must not be an aggregate-only
        artifact (EDGE-5) — the WORST individual OOS window must itself be non-negative. Post-promotion
        (commit a6f608c) the committed baseline ALREADY has a non-negative worst OOS window (the real
        promoted candidate fixed that exact problem for the pre-promotion baseline) — this test now
        asserts the candidate PRESERVES that non-negative-worst-window property while still improving
        mean/std further, not that it fixes a still-losing baseline (there is no longer one)."""
>       candidate_code = _better_candidate_code()
                         ^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_baseline_beat.py:77: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/test_baseline_beat.py:43: in _better_candidate_code
    return patched_baseline_code(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

replacements = (('config.get("edge_weight", 0.25)', 'config.get("edge_weight", 0.4)'), ('config.get("conf_weight", 0.45)', 'config.get("conf_weight", 0.1)'))

    def patched_baseline_code(*replacements: tuple) -> str:
        """Apply a sequence of (old, new) `str.replace(old, new, 1)` edits to the real baseline
        program text. Asserts every replacement actually matched something in the current baseline
        file, so a typo'd test literal fails loudly instead of silently producing a byte-identical
        "candidate" that trivially passes scope_guard for the wrong reason."""
        code = read_baseline_code()
        for old, new in replacements:
>           assert old in code, f"expected baseline text not found (test fixture drifted?): {old!r}"
E           AssertionError: expected baseline text not found (test fixture drifted?): 'config.get("edge_weight", 0.25)'
E           assert 'config.get("edge_weight", 0.25)' in '"""pm_backtest_strategy.py — the self-contained, deterministic, backtestable openevolve program\nthis feature evolves...ost_usd": cost_usd, "net_usd": net, "n_trades": n_trades}\n\n\nif __name__ == "__main__":\n    print(run_backtest())\n'

tests/conftest.py:37: AssertionError
__________ test_full_evaluate_cascade_and_promotion_gate_return_true ___________

tmp_path = PosixPath('/private/var/folders/c1/11fd4j597vx4fb8tnv25y28r0000gn/T/pytest-of-anicca/pytest-18/test_full_evaluate_cascade_and0')

    def test_full_evaluate_cascade_and_promotion_gate_return_true(tmp_path):
>       candidate_code = _better_candidate_code()
                         ^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_baseline_beat.py:95: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/test_baseline_beat.py:43: in _better_candidate_code
    return patched_baseline_code(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

replacements = (('config.get("edge_weight", 0.25)', 'config.get("edge_weight", 0.4)'), ('config.get("conf_weight", 0.45)', 'config.get("conf_weight", 0.1)'))

    def patched_baseline_code(*replacements: tuple) -> str:
        """Apply a sequence of (old, new) `str.replace(old, new, 1)` edits to the real baseline
        program text. Asserts every replacement actually matched something in the current baseline
        file, so a typo'd test literal fails loudly instead of silently producing a byte-identical
        "candidate" that trivially passes scope_guard for the wrong reason."""
        code = read_baseline_code()
        for old, new in replacements:
>           assert old in code, f"expected baseline text not found (test fixture drifted?): {old!r}"
E           AssertionError: expected baseline text not found (test fixture drifted?): 'config.get("edge_weight", 0.25)'
E           assert 'config.get("edge_weight", 0.25)' in '"""pm_backtest_strategy.py — the self-contained, deterministic, backtestable openevolve program\nthis feature evolves...ost_usd": cost_usd, "net_usd": net, "n_trades": n_trades}\n\n\nif __name__ == "__main__":\n    print(run_backtest())\n'

tests/conftest.py:37: AssertionError
____ test_promotion_gate_is_not_trivially_true_adversary_fail_still_blocks _____

tmp_path = PosixPath('/private/var/folders/c1/11fd4j597vx4fb8tnv25y28r0000gn/T/pytest-of-anicca/pytest-18/test_promotion_gate_is_not_tri0')

    def test_promotion_gate_is_not_trivially_true_adversary_fail_still_blocks(tmp_path):
        """Strengthens the "returns True" claim above: the SAME passing candidate must NOT be
        promotable if the fresh adversary verdict is not PASS (REQ-RH4 step 3) or if the trip-wire is
        not clear (REQ-RH4 step 2) — the gate is a real conjunction, not a constant."""
>       candidate_code = _better_candidate_code()
                         ^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_baseline_beat.py:120: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/test_baseline_beat.py:43: in _better_candidate_code
    return patched_baseline_code(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

replacements = (('config.get("edge_weight", 0.25)', 'config.get("edge_weight", 0.4)'), ('config.get("conf_weight", 0.45)', 'config.get("conf_weight", 0.1)'))

    def patched_baseline_code(*replacements: tuple) -> str:
        """Apply a sequence of (old, new) `str.replace(old, new, 1)` edits to the real baseline
        program text. Asserts every replacement actually matched something in the current baseline
        file, so a typo'd test literal fails loudly instead of silently producing a byte-identical
        "candidate" that trivially passes scope_guard for the wrong reason."""
        code = read_baseline_code()
        for old, new in replacements:
>           assert old in code, f"expected baseline text not found (test fixture drifted?): {old!r}"
E           AssertionError: expected baseline text not found (test fixture drifted?): 'config.get("edge_weight", 0.25)'
E           assert 'config.get("edge_weight", 0.25)' in '"""pm_backtest_strategy.py — the self-contained, deterministic, backtestable openevolve program\nthis feature evolves...ost_usd": cost_usd, "net_usd": net, "n_trades": n_trades}\n\n\nif __name__ == "__main__":\n    print(run_backtest())\n'

tests/conftest.py:37: AssertionError
_____ test_evolve_block_only_edit_with_no_denylisted_reference_is_accepted _____

    def test_evolve_block_only_edit_with_no_denylisted_reference_is_accepted():
        # Control case: an EVOLVE-BLOCK-only edit with clean content must PASS, proving the three
        # rejections above fire for the RIGHT reason (scope/denylist), not because ANY edit at all is
        # rejected. Literal updated 2026-07-08 (commit a6f608c promoted a new baseline whose
        # min_confidence default is 7.0, not the pre-promotion 6.0) — this test only needs SOME clean
        # in-scope edit, not any particular beats-baseline property.
        baseline_code = read_baseline_code()
>       candidate_code = patched_baseline_code(
            ('config.get("min_confidence", 7.0)', 'config.get("min_confidence", 9.0)')
        )

tests/test_denylist_reject.py:70: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

replacements = (('config.get("min_confidence", 7.0)', 'config.get("min_confidence", 9.0)'),)

    def patched_baseline_code(*replacements: tuple) -> str:
        """Apply a sequence of (old, new) `str.replace(old, new, 1)` edits to the real baseline
        program text. Asserts every replacement actually matched something in the current baseline
        file, so a typo'd test literal fails loudly instead of silently producing a byte-identical
        "candidate" that trivially passes scope_guard for the wrong reason."""
        code = read_baseline_code()
        for old, new in replacements:
>           assert old in code, f"expected baseline text not found (test fixture drifted?): {old!r}"
E           AssertionError: expected baseline text not found (test fixture drifted?): 'config.get("min_confidence", 7.0)'
E           assert 'config.get("min_confidence", 7.0)' in '"""pm_backtest_strategy.py — the self-contained, deterministic, backtestable openevolve program\nthis feature evolves...ost_usd": cost_usd, "net_usd": net, "n_trades": n_trades}\n\n\nif __name__ == "__main__":\n    print(run_backtest())\n'

tests/conftest.py:37: AssertionError
_ test_regressing_candidate_passes_stage1_but_scores_worse_than_baseline_on_stage2_oos _

tmp_path = PosixPath('/private/var/folders/c1/11fd4j597vx4fb8tnv25y28r0000gn/T/pytest-of-anicca/pytest-18/test_regressing_candidate_pass0')

    def test_regressing_candidate_passes_stage1_but_scores_worse_than_baseline_on_stage2_oos(tmp_path):
        baseline_code = read_baseline_code()
>       candidate_code = _regressing_candidate_code()
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_heldout_regress.py:47: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/test_heldout_regress.py:36: in _regressing_candidate_code
    return patched_baseline_code(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

replacements = (('config.get("min_edge", 0.18)', 'config.get("min_edge", 0.01)'), ('config.get("min_confidence", 7.0)', 'config.get("...ce", 0.85)', 'config.get("max_price", 1.0)'), ('config.get("min_liquidity", 0.4)', 'config.get("min_liquidity", 0.0)'))

    def patched_baseline_code(*replacements: tuple) -> str:
        """Apply a sequence of (old, new) `str.replace(old, new, 1)` edits to the real baseline
        program text. Asserts every replacement actually matched something in the current baseline
        file, so a typo'd test literal fails loudly instead of silently producing a byte-identical
        "candidate" that trivially passes scope_guard for the wrong reason."""
        code = read_baseline_code()
        for old, new in replacements:
>           assert old in code, f"expected baseline text not found (test fixture drifted?): {old!r}"
E           AssertionError: expected baseline text not found (test fixture drifted?): 'config.get("min_edge", 0.18)'
E           assert 'config.get("min_edge", 0.18)' in '"""pm_backtest_strategy.py — the self-contained, deterministic, backtestable openevolve program\nthis feature evolves...ost_usd": cost_usd, "net_usd": net, "n_trades": n_trades}\n\n\nif __name__ == "__main__":\n    print(run_backtest())\n'

tests/conftest.py:37: AssertionError
_____________ test_regressing_candidate_is_not_promoted_end_to_end _____________

tmp_path = PosixPath('/private/var/folders/c1/11fd4j597vx4fb8tnv25y28r0000gn/T/pytest-of-anicca/pytest-18/test_regressing_candidate_is_n0')

    def test_regressing_candidate_is_not_promoted_end_to_end(tmp_path):
        """Full evaluate() cascade + the promotion gate itself: even though the candidate "improved"
        on the cheap stage1 filter, the ordered gate (REQ-RH4) must return False for promotion."""
>       candidate_code = _regressing_candidate_code()
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_heldout_regress.py:73: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/test_heldout_regress.py:36: in _regressing_candidate_code
    return patched_baseline_code(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

replacements = (('config.get("min_edge", 0.18)', 'config.get("min_edge", 0.01)'), ('config.get("min_confidence", 7.0)', 'config.get("...ce", 0.85)', 'config.get("max_price", 1.0)'), ('config.get("min_liquidity", 0.4)', 'config.get("min_liquidity", 0.0)'))

    def patched_baseline_code(*replacements: tuple) -> str:
        """Apply a sequence of (old, new) `str.replace(old, new, 1)` edits to the real baseline
        program text. Asserts every replacement actually matched something in the current baseline
        file, so a typo'd test literal fails loudly instead of silently producing a byte-identical
        "candidate" that trivially passes scope_guard for the wrong reason."""
        code = read_baseline_code()
        for old, new in replacements:
>           assert old in code, f"expected baseline text not found (test fixture drifted?): {old!r}"
E           AssertionError: expected baseline text not found (test fixture drifted?): 'config.get("min_edge", 0.18)'
E           assert 'config.get("min_edge", 0.18)' in '"""pm_backtest_strategy.py — the self-contained, deterministic, backtestable openevolve program\nthis feature evolves...ost_usd": cost_usd, "net_usd": net, "n_trades": n_trades}\n\n\nif __name__ == "__main__":\n    print(run_backtest())\n'

tests/conftest.py:37: AssertionError
__ test_realized_summary_default_path_points_at_the_real_earn_ledger_location __

    def test_realized_summary_default_path_points_at_the_real_earn_ledger_location():
>       assert ledger_reader.DEFAULT_LEDGER_PATH.endswith("anicca/skills/earn/state/earn-ledger.jsonl")
E       AssertionError: assert False
E        +  where False = <built-in method endswith of str object at 0x110acf240>('anicca/skills/earn/state/earn-ledger.jsonl')
E        +    where <built-in method endswith of str object at 0x110acf240> = '/Users/anicca/anicca/.worktrees/self-improve-checkpoint-resume/skills/earn/state/earn-ledger.jsonl'.endswith
E        +      where '/Users/anicca/anicca/.worktrees/self-improve-checkpoint-resume/skills/earn/state/earn-ledger.jsonl' = ledger_reader.DEFAULT_LEDGER_PATH

tests/test_ledger_reader.py:192: AssertionError
_ test_resolved_false_blocks_promotion_unconditionally_even_with_adversary_pass _

tmp_path = PosixPath('/private/var/folders/c1/11fd4j597vx4fb8tnv25y28r0000gn/T/pytest-of-anicca/pytest-18/test_resolved_false_blocks_pro0')

    def test_resolved_false_blocks_promotion_unconditionally_even_with_adversary_pass(tmp_path):
        from lib import promote_gate
    
>       assessment = _eligible_assessment(tmp_path)
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_realized_gate.py:176: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/test_realized_gate.py:145: in _eligible_assessment
    code = patched_baseline_code(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

replacements = (('config.get("edge_weight", 0.25)', 'config.get("edge_weight", 0.4)'), ('config.get("conf_weight", 0.45)', 'config.get("conf_weight", 0.1)'))

    def patched_baseline_code(*replacements: tuple) -> str:
        """Apply a sequence of (old, new) `str.replace(old, new, 1)` edits to the real baseline
        program text. Asserts every replacement actually matched something in the current baseline
        file, so a typo'd test literal fails loudly instead of silently producing a byte-identical
        "candidate" that trivially passes scope_guard for the wrong reason."""
        code = read_baseline_code()
        for old, new in replacements:
>           assert old in code, f"expected baseline text not found (test fixture drifted?): {old!r}"
E           AssertionError: expected baseline text not found (test fixture drifted?): 'config.get("edge_weight", 0.25)'
E           assert 'config.get("edge_weight", 0.25)' in '"""pm_backtest_strategy.py — the self-contained, deterministic, backtestable openevolve program\nthis feature evolves...ost_usd": cost_usd, "net_usd": net, "n_trades": n_trades}\n\n\nif __name__ == "__main__":\n    print(run_backtest())\n'

tests/conftest.py:37: AssertionError
_______ test_gate_none_vacuous_pass_vs_unconditional_block_side_by_side ________

tmp_path = PosixPath('/private/var/folders/c1/11fd4j597vx4fb8tnv25y28r0000gn/T/pytest-of-anicca/pytest-18/test_gate_none_vacuous_pass_vs0')

    def test_gate_none_vacuous_pass_vs_unconditional_block_side_by_side(tmp_path):
        """spec-review F-4: the SAME assessment+adversary-PASS inputs must produce promote:True with
        realized_gate=None (REQ-RL18 vacuous pass) and promote:False with realized_gate={"resolved":
        False, ...} (REQ-RL7 unconditional block) — one test, two assertions, no ambiguity."""
        from lib import promote_gate
    
>       assessment = _eligible_assessment(tmp_path)
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests/test_realized_gate.py:191: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/test_realized_gate.py:145: in _eligible_assessment
    code = patched_baseline_code(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

replacements = (('config.get("edge_weight", 0.25)', 'config.get("edge_weight", 0.4)'), ('config.get("conf_weight", 0.45)', 'config.get("conf_weight", 0.1)'))

    def patched_baseline_code(*replacements: tuple) -> str:
        """Apply a sequence of (old, new) `str.replace(old, new, 1)` edits to the real baseline
        program text. Asserts every replacement actually matched something in the current baseline
        file, so a typo'd test literal fails loudly instead of silently producing a byte-identical
        "candidate" that trivially passes scope_guard for the wrong reason."""
        code = read_baseline_code()
        for old, new in replacements:
>           assert old in code, f"expected baseline text not found (test fixture drifted?): {old!r}"
E           AssertionError: expected baseline text not found (test fixture drifted?): 'config.get("edge_weight", 0.25)'
E           assert 'config.get("edge_weight", 0.25)' in '"""pm_backtest_strategy.py — the self-contained, deterministic, backtestable openevolve program\nthis feature evolves...ost_usd": cost_usd, "net_usd": net, "n_trades": n_trades}\n\n\nif __name__ == "__main__":\n    print(run_backtest())\n'

tests/conftest.py:37: AssertionError
_____ test_leverage_only_candidate_does_not_beat_baseline_on_real_fixture ______

tmp_path = PosixPath('/private/var/folders/c1/11fd4j597vx4fb8tnv25y28r0000gn/T/pytest-of-anicca/pytest-18/test_leverage_only_candidate_d0')

    def test_leverage_only_candidate_does_not_beat_baseline_on_real_fixture(tmp_path):
        """End-to-end (not just the pure-math proof above): a candidate whose ONLY EVOLVE-BLOCK change
        is `base_stake: 5.0 -> 20.0` (identical min_edge/min_confidence thresholds -> identical trade
        selection every window) must score IDENTICALLY to baseline's own risk-adjusted combined_score
        on the real committed fixture, and therefore must NOT beat_baseline (a tie never beats,
        EDGE-2)."""
        leverage_code = patched_baseline_code(('config.get("base_stake", 5.0)', 'config.get("base_stake", 20.0)'))
        leverage_path = write_candidate_with_fixtures(tmp_path, leverage_code)
    
        baseline_stage2 = evaluator.evaluate_stage2(evaluator.BASELINE_PATH)
        leverage_stage2 = evaluator.evaluate_stage2(leverage_path)
    
>       assert math.isclose(leverage_stage2["combined_score"], baseline_stage2["combined_score"], rel_tol=1e-9)
E       assert False
E        +  where False = <built-in function isclose>(2.9014000695008613, 4.015488840463803, rel_tol=1e-09)
E        +    where <built-in function isclose> = math.isclose

tests/test_risk_adjusted_fitness.py:73: AssertionError
____ test_genuine_selection_change_beats_baseline_where_leverage_could_not _____

tmp_path = PosixPath('/private/var/folders/c1/11fd4j597vx4fb8tnv25y28r0000gn/T/pytest-of-anicca/pytest-18/test_genuine_selection_change_0')

    def test_genuine_selection_change_beats_baseline_where_leverage_could_not(tmp_path):
        """Contrast case, same fixture: a genuine selection/sizing-emphasis change (real openevolve
        promotion, commit a6f608c, 2026-07-08 — see test_baseline_beat.py's module docstring for the
        full re-derivation against the NEW committed baseline) DOES beat baseline, unlike the
        leverage-only candidate above — proving `risk_adjusted_score` rewards genuine edge-finding,
        not just any code change."""
        baseline_code = read_baseline_code()
>       selection_code = patched_baseline_code(
            ('config.get("edge_weight", 0.25)', 'config.get("edge_weight", 0.4)'),
            ('config.get("conf_weight", 0.45)', 'config.get("conf_weight", 0.1)'),
        )

tests/test_risk_adjusted_fitness.py:84: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

replacements = (('config.get("edge_weight", 0.25)', 'config.get("edge_weight", 0.4)'), ('config.get("conf_weight", 0.45)', 'config.get("conf_weight", 0.1)'))

    def patched_baseline_code(*replacements: tuple) -> str:
        """Apply a sequence of (old, new) `str.replace(old, new, 1)` edits to the real baseline
        program text. Asserts every replacement actually matched something in the current baseline
        file, so a typo'd test literal fails loudly instead of silently producing a byte-identical
        "candidate" that trivially passes scope_guard for the wrong reason."""
        code = read_baseline_code()
        for old, new in replacements:
>           assert old in code, f"expected baseline text not found (test fixture drifted?): {old!r}"
E           AssertionError: expected baseline text not found (test fixture drifted?): 'config.get("edge_weight", 0.25)'
E           assert 'config.get("edge_weight", 0.25)' in '"""pm_backtest_strategy.py — the self-contained, deterministic, backtestable openevolve program\nthis feature evolves...ost_usd": cost_usd, "net_usd": net, "n_trades": n_trades}\n\n\nif __name__ == "__main__":\n    print(run_backtest())\n'

tests/conftest.py:37: AssertionError
=========================== short test summary info ============================
FAILED tests/test_adversary_disapprove.py::test_good_candidate_is_eligible_for_adversary_review
FAILED tests/test_adversary_disapprove.py::test_adversary_fail_blocks_promotion_even_though_deterministic_gates_pass
FAILED tests/test_adversary_disapprove.py::test_adversary_missing_or_erroring_verdict_also_blocks_promotion_fail_closed
FAILED tests/test_adversary_disapprove.py::test_adversary_pass_on_eligible_candidate_promotes_and_calls_promote_exactly_once
FAILED tests/test_adversary_disapprove.py::test_ineligible_regressing_candidate_never_becomes_eligible_for_adversary_review
FAILED tests/test_baseline_beat.py::test_better_candidate_scope_guard_passes
FAILED tests/test_baseline_beat.py::test_better_candidate_beats_baseline_on_stage2_walk_forward
FAILED tests/test_baseline_beat.py::test_better_candidate_has_non_negative_worst_window_oos
FAILED tests/test_baseline_beat.py::test_full_evaluate_cascade_and_promotion_gate_return_true
FAILED tests/test_baseline_beat.py::test_promotion_gate_is_not_trivially_true_adversary_fail_still_blocks
FAILED tests/test_denylist_reject.py::test_evolve_block_only_edit_with_no_denylisted_reference_is_accepted
FAILED tests/test_heldout_regress.py::test_regressing_candidate_passes_stage1_but_scores_worse_than_baseline_on_stage2_oos
FAILED tests/test_heldout_regress.py::test_regressing_candidate_is_not_promoted_end_to_end
FAILED tests/test_ledger_reader.py::test_realized_summary_default_path_points_at_the_real_earn_ledger_location
FAILED tests/test_realized_gate.py::test_resolved_false_blocks_promotion_unconditionally_even_with_adversary_pass
FAILED tests/test_realized_gate.py::test_gate_none_vacuous_pass_vs_unconditional_block_side_by_side
FAILED tests/test_risk_adjusted_fitness.py::test_leverage_only_candidate_does_not_beat_baseline_on_real_fixture
FAILED tests/test_risk_adjusted_fitness.py::test_genuine_selection_change_beats_baseline_where_leverage_could_not
18 failed, 102 passed, 1 skipped in 2.97s

=== bash -n run_evolve.sh (syntax) ===
OK
