#!/usr/bin/env python3
"""Tests for momentum.py + gate.py (the real strategy edge + the real paper gate). No network/keys/money.
Run: python3 test_strategy.py"""
import momentum
import gate


def approx(a, b, tol=1e-9):
    return abs(a - b) <= tol


# ---- momentum ----
def test_prob_up_neutral_is_half():
    assert approx(momentum.prob_up_from_return(0.0), 0.5)


def test_prob_up_monotonic_and_clamped():
    assert momentum.prob_up_from_return(0.002) > 0.5      # up move -> >0.5
    assert momentum.prob_up_from_return(-0.002) < 0.5     # down move -> <0.5
    assert momentum.prob_up_from_return(1.0) == 0.99      # clamp high
    assert momentum.prob_up_from_return(-1.0) == 0.01     # clamp low


def test_momentum_edge_sign():
    # +0.3% move -> p_up = 0.5+40*0.003 = 0.62; yes at 0.55 -> edge +0.07
    assert approx(momentum.momentum_edge(0.003, 0.55), 0.07)
    # up overpriced: yes at 0.70 -> edge -0.08
    assert approx(momentum.momentum_edge(0.003, 0.70), -0.08)


def test_momentum_edge_bad_price_zero():
    assert momentum.momentum_edge(0.003, 0.0) == 0.0
    assert momentum.momentum_edge(0.003, 1.0) == 0.0


def test_side_picks_positive_edge():
    # strong up move, UP underpriced -> pick UP
    side, price, p = momentum.side_and_prob(0.004, 0.55, 0.45)
    assert side == "UP" and price == 0.55 and p > 0.5
    # strong down move, DOWN underpriced -> pick DOWN
    side, price, p = momentum.side_and_prob(-0.004, 0.55, 0.45)
    assert side == "DOWN" and price == 0.45 and p > 0.5


def test_side_none_when_no_edge():
    # neutral move, both fairly priced -> no side
    side, price, p = momentum.side_and_prob(0.0, 0.51, 0.51)
    assert side is None and price is None and p is None


# ---- gate ----
def test_gate_blocks_small_sample():
    passed, stats = gate.evaluate_gate([{"pnl_usdc": 1.0}] * 5)
    assert passed is False and stats["resolved"] == 5


def test_gate_blocks_low_winrate():
    # 20 trades, 10 win / 10 lose = 0.5 winrate < 0.55 -> FAIL
    rows = [{"pnl_usdc": 1.0}] * 10 + [{"pnl_usdc": -1.0}] * 10
    passed, stats = gate.evaluate_gate(rows)
    assert passed is False and approx(stats["winrate"], 0.5)


def test_gate_blocks_negative_net_even_if_winrate_ok():
    # 12 tiny wins (+0.1) + 8 big losses (-1.0) = winrate 0.6 but net negative -> FAIL
    rows = [{"pnl_usdc": 0.1}] * 12 + [{"pnl_usdc": -1.0}] * 8
    passed, stats = gate.evaluate_gate(rows)
    assert passed is False and stats["net_usdc"] < 0


def test_gate_passes_when_proven():
    # 20 trades, 14 win (+1) / 6 lose (-0.5) -> winrate 0.7, net +11 -> PASS
    rows = [{"pnl_usdc": 1.0}] * 14 + [{"pnl_usdc": -0.5}] * 6
    passed, stats = gate.evaluate_gate(rows)
    assert passed is True and stats["winrate"] >= 0.55 and stats["net_usdc"] >= 0


def test_gate_load_resolved_reads_decide_schema():
    # FIND-002 fix: _load_resolved must actually read decide.py/resolve.py schema rows (src=momentum,
    # status=resolved, pnl_usdc) and IGNORE open rows + foreign (pm-paper.py) rows.
    import json as _j, tempfile, os as _os, pathlib as _p
    fd, path = tempfile.mkstemp(suffix=".jsonl"); _os.close(fd)
    lg = _p.Path(path)
    lg.write_text("\n".join([
        _j.dumps({"src": "momentum", "status": "resolved", "pnl_usdc": 1.5}),      # counts
        _j.dumps({"src": "momentum", "status": "open"}),                            # ignored (open)
        _j.dumps({"status": "resolved", "realized_pnl": 9.9, "shares_held": 3}),    # ignored (pm-paper schema)
        _j.dumps({"src": "momentum", "status": "resolved", "pnl_usdc": -0.5}),      # counts
    ]) + "\n")
    rows = gate._load_resolved(lg)
    _os.unlink(path)
    assert len(rows) == 2, rows
    assert approx(sum(r["pnl_usdc"] for r in rows), 1.0)


def test_settle_math_matches_gate_via_lib():
    # a resolved win at 0.5 for $1 -> pnl +1.0 -> should count as a win in the gate
    import lib as _lib
    pnl = _lib.settle_pnl(True, 0.5, 1.0)
    passed, stats = gate.evaluate_gate([{"pnl_usdc": pnl}] * 20)
    assert stats["winrate"] == 1.0


if __name__ == "__main__":
    import sys
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{len(fns)-failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
