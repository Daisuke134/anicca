#!/usr/bin/env python3
"""RED-first tests for defi-yield/lib.py (pure pool pick + supply sizing). No network/keys/money.
Run: python3 test_lib.py"""
import lib


def approx(a, b, tol=1e-9):
    return abs(a - b) <= tol


def _pools():
    return [
        {"project": "aave-v3", "symbol": "USDC", "tvlUsd": 29_000_000, "apy": 3.14, "pool": "aave1"},
        {"project": "fluid-lending", "symbol": "USDC", "tvlUsd": 9_000_000, "apy": 5.29, "pool": "fluid1"},
        {"project": "some-degen-farm", "symbol": "USDC", "tvlUsd": 50_000_000, "apy": 40.0, "pool": "degen"},
        {"project": "aave-v3", "symbol": "WETH", "tvlUsd": 99_000_000, "apy": 2.0, "pool": "aaveweth"},
        {"project": "spark", "symbol": "USDC", "tvlUsd": 2_000_000, "apy": 6.0, "pool": "sparksmall"},
    ]


def test_pick_excludes_non_allowed_and_non_usdc_and_low_tvl():
    p = lib.pick_pool(_pools())
    # degen-farm (not allowed) excluded despite 40% APY; WETH excluded; spark $2M < $5M min excluded
    assert p is not None and p["project"] == "aave-v3" and p["pool"] == "aave1"


def test_pick_prefer_safest_ranks_bluechip_over_higher_apy():
    # aave-v3 ranks before fluid-lending in ALLOWED -> chosen even though fluid APY higher
    p = lib.pick_pool(_pools(), prefer_safest=True)
    assert p["project"] == "aave-v3"


def test_pick_by_apy_when_not_prefer_safest():
    p = lib.pick_pool(_pools(), prefer_safest=False)
    # highest APY among allowed+USDC+TVL>=5M = fluid 5.29
    assert p["project"] == "fluid-lending"


def test_pick_none_when_nothing_qualifies():
    assert lib.pick_pool([{"project": "aave-v3", "symbol": "USDC", "tvlUsd": 100, "apy": 3}]) is None
    assert lib.pick_pool([]) is None


def test_size_supply_reserves_gas():
    # balance 8, reserve 0.5, max 0.9 -> (8-0.5)*0.9 = 6.75
    assert approx(lib.size_supply(8.0, gas_reserve=0.5, max_pct=0.9), 6.75)


def test_size_supply_zero_below_min():
    # tiny balance -> below min_supply 1.0 -> 0
    assert lib.size_supply(1.2, gas_reserve=0.5, max_pct=0.9, min_supply=1.0) == 0.0
    assert lib.size_supply(0.4, gas_reserve=0.5) == 0.0


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
