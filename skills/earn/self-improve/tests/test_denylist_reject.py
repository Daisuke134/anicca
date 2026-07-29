"""Required test 1 & 2 (delegated task spec): scope_guard.py rejects a candidate that
(1) changes a fixed-region line outside the EVOLVE-BLOCK, and (2) a candidate whose evolvable
region adds a denylisted import/path reference (e.g. `import subprocess` / a wallet-key path).

Traces to behavioral-spec.md REQ-DL1/DL2/DL4/DL5, verification-architecture.md
PROP-SI-DL2/DL4/DL5. INV-3: `# EVOLVE-BLOCK-START/END` markers provide NO enforcement of their
own — `scope_guard.check()` is the entire enforcement mechanism, exercised here directly.
"""
from unittest import mock

import evaluator
from conftest import patched_baseline_code, read_baseline_code, write_candidate_with_fixtures
from lib import scope_guard


def test_rejects_candidate_that_changes_a_fixed_region_line():
    baseline_code = read_baseline_code()
    # Alter ONE line strictly OUTSIDE the EVOLVE-BLOCK — the FIXTURE_PATH assignment, part of the
    # fixed fixture-loader region — while leaving the EVOLVE-BLOCK itself byte-identical.
    candidate_code = patched_baseline_code(
        (
            'FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "pm_history.csv")',
            'FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "tampered.csv")',
        )
    )

    ok, reason = scope_guard.check(candidate_code, baseline_code)

    assert ok is False
    assert "out-of-scope" in reason


def test_rejects_evolve_block_that_adds_a_subprocess_import():
    baseline_code = read_baseline_code()
    candidate_code = patched_baseline_code(
        (
            "# EVOLVE-BLOCK-START\n",
            "# EVOLVE-BLOCK-START\nimport subprocess  # smuggled process-spawn capability\n",
        )
    )

    ok, reason = scope_guard.check(candidate_code, baseline_code)

    assert ok is False
    assert "denylisted" in reason


def test_rejects_evolve_block_that_references_a_wallet_key_path():
    baseline_code = read_baseline_code()
    candidate_code = patched_baseline_code(
        (
            "# EVOLVE-BLOCK-START\n",
            '# EVOLVE-BLOCK-START\n_LEAK = "~/.automaton/solana.json"  # smuggled wallet-key path\n',
        )
    )

    ok, reason = scope_guard.check(candidate_code, baseline_code)

    assert ok is False
    assert "denylisted" in reason


def test_evolve_block_only_edit_with_no_denylisted_reference_is_accepted():
    # Control case: an EVOLVE-BLOCK-only edit with clean content must PASS, proving the three
    # rejections above fire for the RIGHT reason (scope/denylist), not because ANY edit at all is
    # rejected. Literal updated 2026-07-08 (commit a6f608c promoted a new baseline whose
    # min_confidence default is 7.5) — this test only needs SOME clean
    # in-scope edit, not any particular beats-baseline property.
    baseline_code = read_baseline_code()
    candidate_code = patched_baseline_code(
        ('config.get("min_confidence", 7.5)', 'config.get("min_confidence", 9.0)')
    )

    ok, reason = scope_guard.check(candidate_code, baseline_code)

    assert ok is True
    assert reason == "scope-guard-pass"


def test_scope_guard_rejection_is_wired_as_stage1s_first_operation(tmp_path):
    """REQ-DL5: evaluate_stage1 calls scope_guard BEFORE any backtest computation, and a rejected
    candidate short-circuits evaluate() before evaluate_stage2 is ever invoked."""
    candidate_code = patched_baseline_code(
        (
            "# EVOLVE-BLOCK-START\n",
            "# EVOLVE-BLOCK-START\nimport subprocess  # smuggled process-spawn capability\n",
        )
    )
    candidate_path = write_candidate_with_fixtures(tmp_path, candidate_code)

    with mock.patch.object(evaluator, "evaluate_stage2") as mocked_stage2:
        result = evaluator.evaluate(candidate_path)

    mocked_stage2.assert_not_called()
    assert result["stage1_pass"] is False
    assert result["stage2_pass"] is False
    assert result["combined_score"] == evaluator.FAIL_SENTINEL
    assert "denylisted" in result["artifacts"]["scope_guard_verdict"]
