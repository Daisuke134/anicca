#!/usr/bin/env python3
"""Tests for resolve.py (the critical resolver, fixes FIND-004 untested) + decide.py dedup helpers.
Injects a deterministic outcome_fn so no network/money is needed. Run: python3 test_resolve.py"""
import json
import os
import tempfile
import pathlib
import resolve
import decide


def approx(a, b, tol=1e-9):
    return abs(a - b) <= tol


def _ledger(rows):
    fd, p = tempfile.mkstemp(suffix=".jsonl"); os.close(fd)
    lg = pathlib.Path(p)
    lg.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return lg


def test_resolve_marks_win_and_loss_with_injected_outcome():
    # UP side, window closed up -> win; DOWN side same window -> loss. entry 0.5, size 1 -> win pnl +1, loss -1.
    rows = [
        {"src": "momentum", "status": "open", "side": "UP", "entry_price": 0.5, "size_usdc": 1.0,
         "window_start_ms": 1000, "window_end_ms": 2000},
        {"src": "momentum", "status": "open", "side": "DOWN", "entry_price": 0.5, "size_usdc": 1.0,
         "window_start_ms": 1000, "window_end_ms": 2000},
    ]
    lg = _ledger(rows)
    n, pnls = resolve.resolve_all(ledger=lg, now_ms=9999, outcome_fn=lambda ws: True)  # closed UP
    got = [json.loads(l) for l in lg.read_text().splitlines() if l.strip()]
    os.unlink(lg)
    assert n == 2
    up = next(r for r in got if r["side"] == "UP"); dn = next(r for r in got if r["side"] == "DOWN")
    assert up["status"] == "resolved" and up["won"] is True and approx(up["pnl_usdc"], 1.0)
    assert dn["status"] == "resolved" and dn["won"] is False and approx(dn["pnl_usdc"], -1.0)


def test_resolve_leaves_open_before_window_end():
    rows = [{"src": "momentum", "status": "open", "side": "UP", "entry_price": 0.5, "size_usdc": 1.0,
             "window_start_ms": 1000, "window_end_ms": 5000}]
    lg = _ledger(rows)
    n, _ = resolve.resolve_all(ledger=lg, now_ms=3000, outcome_fn=lambda ws: True)  # now < window_end
    got = json.loads(lg.read_text().splitlines()[0]); os.unlink(lg)
    assert n == 0 and got["status"] == "open"


def test_resolve_leaves_open_when_outcome_unavailable():
    rows = [{"src": "momentum", "status": "open", "side": "UP", "entry_price": 0.5, "size_usdc": 1.0,
             "window_start_ms": 1000, "window_end_ms": 2000}]
    lg = _ledger(rows)
    n, _ = resolve.resolve_all(ledger=lg, now_ms=9999, outcome_fn=lambda ws: None)  # data unavailable
    got = json.loads(lg.read_text().splitlines()[0]); os.unlink(lg)
    assert n == 0 and got["status"] == "open"


def test_resolve_ignores_foreign_rows():
    rows = [{"status": "open", "realized_pnl": 1, "shares_held": 3}]  # pm-paper schema, not momentum
    lg = _ledger(rows)
    n, _ = resolve.resolve_all(ledger=lg, now_ms=9999, outcome_fn=lambda ws: True)
    os.unlink(lg)
    assert n == 0


def test_dedup_one_trade_per_window_any_side():
    rows = [{"src": "momentum", "window_end_ms": 2000, "side": "UP"}]
    lg = _ledger(rows)
    # a later DOWN signal for the SAME window must be blocked (one trade per window)
    assert decide._already_traded_window(lg, 2000) is True
    assert decide._already_traded_window(lg, 3000) is False   # different window ok
    os.unlink(lg)


if __name__ == "__main__":
    import sys
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn(); print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1; print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{len(fns)-failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
