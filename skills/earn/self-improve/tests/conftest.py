"""Shared test scaffolding for the self-improve harness's deterministic-core test suite.

Puts `skills/earn/self-improve/` on sys.path so tests can `import evaluator` and
`from lib import gate_math, scope_guard, promote` the same way evaluator.py itself does. Also
provides small helpers for constructing synthetic "candidate program" files (whole-file text, the
ACTUAL child_code shape scope_guard.py and evaluator.py operate on — never a raw diff object) that
carry their own copy of the real historical fixture so `load_fixture()`/`run_backtest()` work when
evaluator.py dynamically imports them.
"""
from __future__ import annotations

import os
import shutil
import sys

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SELF_IMPROVE_DIR = os.path.dirname(TESTS_DIR)
if SELF_IMPROVE_DIR not in sys.path:
    sys.path.insert(0, SELF_IMPROVE_DIR)

BASELINE_PATH = os.path.join(SELF_IMPROVE_DIR, "strategies", "pm_backtest_strategy.py")
FIXTURE_SRC_PATH = os.path.join(SELF_IMPROVE_DIR, "strategies", "fixtures", "pm_history.csv")


def read_baseline_code() -> str:
    with open(BASELINE_PATH, "r", encoding="utf-8") as f:
        return f.read()


def patched_baseline_code(*replacements: tuple) -> str:
    """Apply a sequence of (old, new) `str.replace(old, new, 1)` edits to the real baseline
    program text. Asserts every replacement actually matched something in the current baseline
    file, so a typo'd test literal fails loudly instead of silently producing a byte-identical
    "candidate" that trivially passes scope_guard for the wrong reason."""
    code = read_baseline_code()
    for old, new in replacements:
        assert old in code, f"expected baseline text not found (test fixture drifted?): {old!r}"
        code = code.replace(old, new, 1)
    return code


def write_candidate_with_fixtures(tmp_path, candidate_code: str, filename: str = "candidate.py") -> str:
    """Write `candidate_code` to `tmp_path/filename` and copy the real historical fixture CSV
    alongside it at `tmp_path/fixtures/pm_history.csv`, so the candidate's own
    `FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "pm_history.csv")` (computed
    relative to ITS OWN `__file__`) resolves correctly once evaluator.py dynamically imports it.
    Returns the candidate file's absolute path (str) for passing to evaluate()/evaluate_stage1()."""
    candidate_path = tmp_path / filename
    candidate_path.write_text(candidate_code, encoding="utf-8")
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir(exist_ok=True)
    shutil.copy(FIXTURE_SRC_PATH, fixtures_dir / "pm_history.csv")
    return str(candidate_path)
