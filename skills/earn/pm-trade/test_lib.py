#!/usr/bin/env python3
"""RED-first tests for pm-trade/lib.py pure decision math. Run: python3 -m pytest test_lib.py -q
(or `python3 test_lib.py`). No network, no keys, no money."""
import lib


def approx(a, b, tol=1e-9):
    return abs(a - b) <= tol


def test_edge_signed():
    assert approx(lib.edge(0.7, 0.5), 0.2)
    assert approx(lib.edge(0.4, 0.5), -0.1)


def test_kelly_fraction_favorable():
    # q=0.7, p=0.5 -> (0.7-0.5)/(1-0.5) = 0.4
    assert approx(lib.kelly_fraction(0.7, 0.5), 0.4)


def test_kelly_fraction_unfavorable_is_zero():
    assert lib.kelly_fraction(0.4, 0.5) == 0.0
    assert lib.kelly_fraction(0.5, 0.5) == 0.0


def test_kelly_fraction_degenerate_price_is_zero():
    assert lib.kelly_fraction(0.9, 1.0) == 0.0   # p>=1
    assert lib.kelly_fraction(0.9, 0.0) == 0.0   # p<=0


def test_position_size_quarter_kelly_and_cap():
    # q=0.8, p=0.5, bankroll=100. full kelly=(0.3/0.5)=0.6, quarter=0.15 -> stake 15,
    # capped at max_bet_pct 0.05*100=5 -> expect 5.
    s = lib.position_size(0.8, 0.5, 100.0, kelly_frac=0.25, max_bet_pct=0.05, min_edge=0.15)
    assert approx(s, 5.0), s


def test_position_size_below_min_edge_is_zero():
    # edge 0.1 < min_edge 0.15 -> 0
    assert lib.position_size(0.6, 0.5, 100.0, min_edge=0.15) == 0.0


def test_position_size_respects_gas_reserve():
    # bankroll below reserve -> 0
    assert lib.position_size(0.9, 0.3, 0.4, gas_reserve=0.5) == 0.0


def test_arb_pair_profit_when_underpriced():
    # YES 0.48 + NO 0.49 = 0.97 -> profit 0.03 per $1 pair
    assert approx(lib.arb_pair_profit(0.48, 0.49), 0.03)


def test_arb_pair_profit_zero_when_no_edge():
    assert lib.arb_pair_profit(0.55, 0.55) == 0.0   # sum 1.10 >= 1
    assert lib.arb_pair_profit(0.5, 0.5) == 0.0     # sum exactly 1.0


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
