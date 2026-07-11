#!/usr/bin/env python3
"""Pure-logic tests for no_naked.py + positions.parse_positions_by_token (SPEC-no-naked-fills.md
R5). NEVER touches a wallet, the CLOB, or the network — all inputs are mock dicts/JSON strings.

Run: python3 -m pytest test_no_naked.py -q     (or: python3 test_no_naked.py)
"""
import json

from no_naked import naked_legs, plan_naked_fix, plan_arb_unwind
from positions import parse_positions_by_token

PAIR = {"market": "MktA", "yes_token": "111", "no_token": "222"}


# ---- naked_legs -----------------------------------------------------------
def test_single_leg_is_naked():
    holdings = [{"asset": "111", "size": 5}]  # hold YES only
    out = naked_legs(holdings, [PAIR])
    assert len(out) == 1
    assert out[0]["held_token"] == "111"
    assert out[0]["missing_token"] == "222"
    assert out[0]["held_size"] == 5


def test_single_leg_naked_no_side():
    holdings = [{"asset": "222", "size": 7}]  # hold NO only
    out = naked_legs(holdings, [PAIR])
    assert len(out) == 1
    assert out[0]["held_token"] == "222"
    assert out[0]["missing_token"] == "111"


def test_both_legs_is_bundle_not_naked():
    holdings = [{"asset": "111", "size": 5}, {"asset": "222", "size": 5}]
    assert naked_legs(holdings, [PAIR]) == []


def test_zero_holdings_not_naked():
    assert naked_legs([], [PAIR]) == []
    assert naked_legs([{"asset": "111", "size": 0}], [PAIR]) == []


def test_malformed_holdings_are_ignored():
    holdings = [None, {"nope": 1}, {"asset": "111", "size": "bad"}, {"asset": "111", "size": 5}]
    out = naked_legs(holdings, [PAIR])
    assert len(out) == 1 and out[0]["held_size"] == 5


# ---- plan_naked_fix -------------------------------------------------------
def test_fix_prefers_complete_when_cheaper():
    leg = {"held_token": "111", "held_size": 5, "missing_token": "222", "market": "MktA"}
    # missing_ask 0.30 -> complete keeps (1-0.30)=0.70/sh ; held_bid 0.40 -> sell keeps 0.40
    plan = plan_naked_fix(leg, {"missing_ask": 0.30, "held_bid": 0.40})
    assert plan["action"] == "complete"
    assert plan["token"] == "222"
    assert plan["size"] == 5


def test_fix_prefers_sell_when_cheaper():
    leg = {"held_token": "111", "held_size": 5, "missing_token": "222", "market": "MktA"}
    # missing_ask 0.90 -> complete keeps 0.10/sh ; held_bid 0.55 -> sell keeps 0.55
    plan = plan_naked_fix(leg, {"missing_ask": 0.90, "held_bid": 0.55})
    assert plan["action"] == "sell"
    assert plan["token"] == "111"


def test_fix_forced_to_sell_when_no_ask():
    leg = {"held_token": "111", "held_size": 5, "missing_token": "222", "market": "MktA"}
    plan = plan_naked_fix(leg, {"missing_ask": None, "held_bid": 0.55})
    assert plan["action"] == "sell"


def test_fix_forced_to_complete_when_no_bid():
    leg = {"held_token": "111", "held_size": 5, "missing_token": "222", "market": "MktA"}
    plan = plan_naked_fix(leg, {"missing_ask": 0.30, "held_bid": None})
    assert plan["action"] == "complete"


def test_fix_none_when_no_liquidity():
    leg = {"held_token": "111", "held_size": 5, "missing_token": "222", "market": "MktA"}
    plan = plan_naked_fix(leg, {"missing_ask": None, "held_bid": None})
    assert plan["action"] == "none"


# ---- plan_arb_unwind ------------------------------------------------------
def test_arb_partial_fill_triggers_unwind():
    legs = [{"token": "111", "filled": True}, {"token": "222", "filled": False}]
    out = plan_arb_unwind(legs)
    assert out == [{"action": "unwind", "token": "111"}]


def test_arb_both_filled_no_unwind():
    legs = [{"token": "111", "filled": True}, {"token": "222", "filled": True}]
    assert plan_arb_unwind(legs) == []


def test_arb_none_filled_no_unwind():
    legs = [{"token": "111", "filled": False}, {"token": "222", "filled": False}]
    assert plan_arb_unwind(legs) == []


# ---- positions.parse_positions_by_token -----------------------------------
def test_parse_positions_by_token_happy():
    raw = json.dumps([
        {"asset": "111", "conditionId": "0xcond", "title": "MktA", "size": 5, "currentValue": 4.9},
        {"asset": "222", "conditionId": "0xcond", "title": "MktA", "size": 0, "currentValue": 0.0},
    ])
    rows = parse_positions_by_token(raw)
    assert len(rows) == 2
    assert rows[0]["asset"] == "111" and rows[0]["size"] == 5.0
    assert rows[0]["conditionId"] == "0xcond" and rows[0]["market"] == "MktA"


def test_parse_positions_by_token_failclosed():
    assert parse_positions_by_token("not json") == []
    assert parse_positions_by_token("{}") == []
    assert parse_positions_by_token(json.dumps([1, "x", None])) == []


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
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
