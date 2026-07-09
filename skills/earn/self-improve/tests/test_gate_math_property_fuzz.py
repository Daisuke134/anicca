"""VCSDD Phase 5 (formal hardening) — property-based / total-domain strengthening for
self-improve-real-ledger's new pure `gate_math.py` functions
(`realized_window_split`/`is_worsening_trend`/`realized_trend_blocks`/`data_realism_gap`).

The 8-combination truth table for `is_worsening_trend`/`realized_trend_blocks`
(tests/test_realized_gate.py::test_realized_trend_blocks_8_combination_truth_table) is already
EXHAUSTIVE over its 3-boolean-ish input domain (2**3 = 8, all 8 present) — not duplicated here.
This file adds what that pytest-parametrize style cannot cheaply give: (1) a property proved over
many RANDOMLY GENERATED row lists for `realized_window_split`'s split invariant, rather than a
handful of hand-picked fixtures, and (2) precise numeric-boundary fuzzing for
`data_realism_gap`'s `multiple=3.0` cutoff.

Requires `hypothesis` (test-only dependency, NOT added to any production requirements file — see
verification/security-report.md's Tooling section for the exact install command used). Skipped
gracefully (not a failure) if hypothesis is unavailable in the interpreter running pytest, so this
file never breaks the regular fast 84-test suite for a contributor without it installed.
"""
import math

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, settings, strategies as st  # noqa: E402

from lib import gate_math  # noqa: E402


# ============================================================================
# PROP-RL-GATE2 strengthening — realized_window_split's split invariant
# ============================================================================

_ts_strategy = st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False)
_net_strategy = st.floats(min_value=-1_000.0, max_value=1_000.0, allow_nan=False, allow_infinity=False)
_row_strategy = st.tuples(_ts_strategy, _net_strategy)


@given(
    rows=st.lists(_row_strategy, min_size=0, max_size=40),
    window_start_ts=_ts_strategy,
    window_span=st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=300, deadline=None)
def test_realized_window_split_invariant_first_plus_second_equals_window_net(rows, window_start_ts, window_span):
    """REQ-RL8's core invariant, proved over hundreds of randomly generated (ts, net_usdc) row
    lists rather than a handful of hand-picked fixtures: first_half + second_half ALWAYS equals
    the reported window_net, for ANY row list / window (including rows entirely outside the
    window, empty lists, and windows of zero width)."""
    window_end_ts = window_start_ts + window_span
    result = gate_math.realized_window_split(rows, window_start_ts, window_end_ts)
    total = result["first_half_net_usd"] + result["second_half_net_usd"]
    assert math.isclose(total, result["window_net_usd"], rel_tol=1e-9, abs_tol=1e-9)
    assert result["row_count"] >= 0
    assert result["row_count"] <= len(rows)


def test_realized_window_split_empty_list_is_all_zero():
    result = gate_math.realized_window_split([], window_start_ts=0.0, window_end_ts=100.0)
    assert result == {
        "window_net_usd": 0.0,
        "first_half_net_usd": 0.0,
        "second_half_net_usd": 0.0,
        "row_count": 0,
    }


def test_realized_window_split_single_row_before_midpoint():
    result = gate_math.realized_window_split([(10.0, 5.0)], window_start_ts=0.0, window_end_ts=100.0)
    assert result["row_count"] == 1
    assert result["first_half_net_usd"] == 5.0
    assert result["second_half_net_usd"] == 0.0


def test_realized_window_split_single_row_after_midpoint():
    result = gate_math.realized_window_split([(90.0, 5.0)], window_start_ts=0.0, window_end_ts=100.0)
    assert result["row_count"] == 1
    assert result["first_half_net_usd"] == 0.0
    assert result["second_half_net_usd"] == 5.0


def test_realized_window_split_all_rows_before_window():
    rows = [(-10.0, 100.0), (-5.0, 200.0)]
    result = gate_math.realized_window_split(rows, window_start_ts=0.0, window_end_ts=100.0)
    assert result["row_count"] == 0
    assert result["window_net_usd"] == 0.0


def test_realized_window_split_all_rows_after_window():
    rows = [(150.0, 100.0), (200.0, 200.0)]
    result = gate_math.realized_window_split(rows, window_start_ts=0.0, window_end_ts=100.0)
    assert result["row_count"] == 0
    assert result["window_net_usd"] == 0.0


def test_realized_window_split_row_exactly_at_midpoint_goes_to_second_half():
    # midpoint of [0, 100) is 50.0; the function's own `else` branch (ts >= midpoint) means an
    # exact-midpoint row belongs to the SECOND half — this is the documented tie-break, pinned
    # here as an explicit regression guard.
    result = gate_math.realized_window_split([(50.0, 7.0)], window_start_ts=0.0, window_end_ts=100.0)
    assert result["first_half_net_usd"] == 0.0
    assert result["second_half_net_usd"] == 7.0


def test_realized_window_split_row_exactly_at_window_start_is_included():
    result = gate_math.realized_window_split([(0.0, 3.0)], window_start_ts=0.0, window_end_ts=100.0)
    assert result["row_count"] == 1


def test_realized_window_split_row_exactly_at_window_end_is_excluded():
    # half-open window [start, end) — REQ-RL8's own documented convention.
    result = gate_math.realized_window_split([(100.0, 3.0)], window_start_ts=0.0, window_end_ts=100.0)
    assert result["row_count"] == 0


# ============================================================================
# PROP-RL-GATE4 strengthening — data_realism_gap's multiple=3.0 boundary, fuzzed precisely
# ============================================================================


@pytest.mark.parametrize(
    "mean_backtest_net_usd,mean_realized_net_per_row,expected",
    [
        (2.999, 1.0, False),  # just under 3x -> not implausible
        (3.0, 1.0, False),  # exactly 3x -> strict > required, does NOT fire (PROP-RL-GATE4)
        (3.0001, 1.0, True),  # just over 3x -> fires
        (2.9999999, 1.0, False),
        (3.0000001, 1.0, True),
    ],
)
def test_data_realism_gap_multiple_boundary_is_exactly_strict_greater_than(
    mean_backtest_net_usd, mean_realized_net_per_row, expected
):
    assert (
        gate_math.data_realism_gap(
            mean_backtest_net_usd=mean_backtest_net_usd,
            mean_realized_net_per_row=mean_realized_net_per_row,
            sufficient=True,
            multiple=3.0,
        )
        is expected
    )


@given(
    mean_backtest_net_usd=st.floats(min_value=0.01, max_value=10_000.0, allow_nan=False, allow_infinity=False),
    mean_realized_net_per_row=st.floats(min_value=0.01, max_value=10_000.0, allow_nan=False, allow_infinity=False),
    multiple=st.floats(min_value=1.0, max_value=10.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=300, deadline=None)
def test_data_realism_gap_case_b_matches_is_implausible_jump_exactly(
    mean_backtest_net_usd, mean_realized_net_per_row, multiple
):
    """Cross-check property: for any positive (mean_backtest_net_usd, mean_realized_net_per_row,
    multiple) triple with sufficient=True, data_realism_gap's case-(b) branch must agree EXACTLY
    with a direct call to the already-proven-pure is_implausible_jump (which it is documented to
    reuse, REQ-RL11) — proving no drift between the two independent call sites."""
    expected = gate_math.is_implausible_jump(mean_backtest_net_usd, mean_realized_net_per_row, multiple)
    actual = gate_math.data_realism_gap(
        mean_backtest_net_usd=mean_backtest_net_usd,
        mean_realized_net_per_row=mean_realized_net_per_row,
        sufficient=True,
        multiple=multiple,
    )
    assert actual == expected


@given(
    mean_backtest_net_usd=st.floats(min_value=-10_000.0, max_value=10_000.0, allow_nan=False, allow_infinity=False),
    mean_realized_net_per_row=st.floats(min_value=-10_000.0, max_value=10_000.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=300, deadline=None)
def test_data_realism_gap_never_fires_when_insufficient_total_domain(mean_backtest_net_usd, mean_realized_net_per_row):
    """sufficient=False must vacuously block this entire gate for ANY input pair, fuzzed across
    the full positive/negative/zero domain (not just the two hand-picked cases already in
    test_realized_gate.py)."""
    assert (
        gate_math.data_realism_gap(
            mean_backtest_net_usd=mean_backtest_net_usd,
            mean_realized_net_per_row=mean_realized_net_per_row,
            sufficient=False,
        )
        is False
    )


# ============================================================================
# is_worsening_trend — property over the full float domain (truth table already exhaustive at
# the boolean-combination level; this proves the strict-< itself holds for arbitrary magnitudes).
# ============================================================================


@given(
    first_half_net_usd=st.floats(min_value=-1e9, max_value=1e9, allow_nan=False, allow_infinity=False),
    second_half_net_usd=st.floats(min_value=-1e9, max_value=1e9, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=200, deadline=None)
def test_is_worsening_trend_matches_python_strict_less_than(first_half_net_usd, second_half_net_usd):
    assert gate_math.is_worsening_trend(first_half_net_usd, second_half_net_usd) == (
        second_half_net_usd < first_half_net_usd
    )
