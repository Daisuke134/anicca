"""fills.py — PURE fill-selection + P&L-split functions (Group B: REQ-B1, REQ-B2, REQ-B3).

No I/O, no clock reads, no subprocess — dict-in/list-in, dict-out/list-out only. See
behavioral-spec.md Group B and verification-architecture.md's purity boundary map (this module
is the "PURE" row of that table).
"""
from __future__ import annotations


def compute_realized_pnl(closed_pnl, fee) -> dict:
    """REQ-B1: split a settled fill's closedPnl/fee into ledger-line earn/cost buckets.

    net_usdc always equals closed_pnl - fee exactly; only which bucket (earn vs cost)
    absorbs the fee changes with the win/loss split.
    """
    closed_pnl = float(closed_pnl)
    fee = float(fee)
    if closed_pnl > 0:
        earn_usdc = closed_pnl
        cost_usdc = fee
    else:
        earn_usdc = 0
        cost_usdc = fee + (-closed_pnl)
    return {"earn_usdc": earn_usdc, "cost_usdc": cost_usdc, "net_usdc": earn_usdc - cost_usdc}


def _closed_pnl_is_zero(fill: dict) -> bool:
    """True only when closedPnl parses cleanly to exactly 0. A non-numeric/missing closedPnl is
    NOT excluded here — REQ-B3/REQ-B4.2's UNPROCESSABLE/STOP handling is the only place that
    ever classifies or rejects such a fill (this selector must never silently drop it)."""
    try:
        return float(fill.get("closedPnl")) == 0
    except (TypeError, ValueError):
        return False


def select_close_fills(fills: list, since_time_ms: int) -> list:
    """REQ-B2: fills with time >= since_time_ms (INCLUSIVE — REQ-B8) AND a numeric, non-zero
    closedPnl, sorted ascending by time. A fill with an unparseable closedPnl is kept (not
    excluded) so REQ-B3/REQ-B4.2's STOP logic sees it."""
    candidates = [
        f for f in fills
        if f.get("time", -1) >= since_time_ms and not _closed_pnl_is_zero(f)
    ]
    return sorted(candidates, key=lambda f: f["time"])


def is_unprocessable(fill: dict) -> bool:
    """REQ-B3: True iff closedPnl/fee is missing or non-numeric, OR tid is missing or not an
    int. Never invents a value — this is purely a classification, no coercion is applied to the
    fill itself."""
    try:
        float(fill["closedPnl"])
    except (KeyError, TypeError, ValueError):
        return True
    try:
        float(fill["fee"])
    except (KeyError, TypeError, ValueError):
        return True
    tid = fill.get("tid")
    if not isinstance(tid, int) or isinstance(tid, bool):
        return True
    return False
