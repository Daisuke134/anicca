"""Unit tests — PURE layer (skills/earn/hl-trade/lib/fills.py, NOT YET IMPLEMENTED).

RED phase (VCSDD Phase 2a). No network, no filesystem, no subprocess — fixture data only
(REQ-E5 / anti-fake gate: pure-function unit tests may use fixtures, never live calls).

Covers verification-architecture.md PROP-001, PROP-002, PROP-002b, PROP-003
(behavioral-spec.md REQ-B1, REQ-B2, REQ-B3).

Public API this file defines by import (fills.py does not exist yet — every test in this file
is expected to fail at collection with ModuleNotFoundError until Phase 2b implements it):
  compute_realized_pnl(closed_pnl: float, fee: float) -> dict[str, float]
      {"earn_usdc": ..., "cost_usdc": ..., "net_usdc": ...}
  select_close_fills(fills: list[dict], since_time_ms: int) -> list[dict]
      INCLUSIVE of since_time_ms (REQ-B2/REQ-B8); excludes closedPnl == 0; sorted ascending
      by "time". A fill whose closedPnl cannot be parsed as a number is NOT silently dropped
      here — it is left in the candidate list so the caller's is_unprocessable/REQ-B4.2 STOP
      logic (not this pure selector) is the one place that ever classifies/rejects it.
  is_unprocessable(fill: dict) -> bool
      True iff closedPnl/fee is missing or non-numeric, OR tid is missing or not an int.
"""
from fills import compute_realized_pnl, select_close_fills, is_unprocessable  # noqa: E402


# --- PROP-001 (REQ-B1): win/loss/breakeven split; net_usdc always == closed_pnl - fee exactly ---

def test_compute_realized_pnl_win_charges_fee_against_earn_only():
    r = compute_realized_pnl(2.0, 0.3)
    assert r == {"earn_usdc": 2.0, "cost_usdc": 0.3, "net_usdc": 1.7}
    assert abs(r["net_usdc"] - (2.0 - 0.3)) < 1e-9


def test_compute_realized_pnl_loss_folds_fee_into_cost():
    r = compute_realized_pnl(-1.0, 0.2)
    assert r == {"earn_usdc": 0, "cost_usdc": 1.2, "net_usdc": -1.2}
    assert abs(r["net_usdc"] - (-1.0 - 0.2)) < 1e-9


def test_compute_realized_pnl_exact_breakeven_still_charges_fee():
    r = compute_realized_pnl(0, 0.1)
    assert r == {"earn_usdc": 0, "cost_usdc": 0.1, "net_usdc": -0.1}
    assert abs(r["net_usdc"] - (0 - 0.1)) < 1e-9


# --- PROP-002 (REQ-B2): time>=since filter, closedPnl==0 excluded, ascending sort ---

def test_select_close_fills_excludes_zero_pnl_and_time_strictly_before_since():
    fills = [
        {"time": 90, "closedPnl": "2.0"},
        {"time": 100, "closedPnl": "0.0"},
        {"time": 150, "closedPnl": "1.5"},
    ]
    result = select_close_fills(fills, since_time_ms=100)
    assert result == [{"time": 150, "closedPnl": "1.5"}]


# --- PROP-002b (REQ-B2/REQ-B8 inclusive boundary, tied timestamp — F-1 money-safety capstone) ---

def test_select_close_fills_boundary_is_inclusive_not_exclusive():
    fills = [
        {"time": 100, "tid": 1, "closedPnl": "2.0"},
        {"time": 100, "tid": 2, "closedPnl": "1.5"},
        {"time": 150, "tid": 3, "closedPnl": "1.0"},
    ]
    result = select_close_fills(fills, since_time_ms=100)
    tids = [f["tid"] for f in result]
    assert tids == [1, 2, 3], (
        "boundary must be time >= since_time_ms, NOT time > since_time_ms — a strictly-"
        "greater-than implementation silently drops both tid=1 and tid=2 at "
        "time == since_time_ms, which is exactly the money-safety defect REQ-B8 forbids"
    )


def test_select_close_fills_sorts_ascending_by_time_even_if_input_is_unsorted():
    fills = [
        {"time": 150, "tid": 3, "closedPnl": "1.0"},
        {"time": 90, "tid": 1, "closedPnl": "2.0"},
        {"time": 120, "tid": 2, "closedPnl": "3.0"},
    ]
    result = select_close_fills(fills, since_time_ms=0)
    assert [f["tid"] for f in result] == [1, 2, 3]


# --- PROP-003 (REQ-B3): UNPROCESSABLE classification — never invent a value ---

def test_is_unprocessable_true_for_non_numeric_closed_pnl():
    assert is_unprocessable({"closedPnl": "abc", "fee": "0.1", "tid": 1}) is True


def test_is_unprocessable_true_for_missing_fee():
    assert is_unprocessable({"closedPnl": "1.0", "tid": 1}) is True


def test_is_unprocessable_true_for_missing_tid():
    assert is_unprocessable({"closedPnl": "1.0", "fee": "0.1"}) is True


def test_is_unprocessable_true_for_non_integer_tid():
    assert is_unprocessable({"closedPnl": "1.0", "fee": "0.1", "tid": "not-an-int"}) is True


def test_is_unprocessable_false_for_well_formed_live_hl_api_shape():
    # numeric-string closedPnl/fee + a real Python int tid — the actual live shape confirmed in
    # evidence/audit-userfills-summary.md (146/146 real fills). Must NOT be flagged.
    assert is_unprocessable({"closedPnl": "1.23", "fee": "0.01", "tid": 568915744567876}) is False
