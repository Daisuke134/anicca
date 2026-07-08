"""test_capital_gate_and_scale_down.py — RED (Phase 2a, feature claude-p-ceo-loop).
PROP-CEO-007 (M4修正, REQ-CEO-030): capital_increase_within_realized_profit + the M4 disproof
(realized_profit_usd()-converted value, never the raw JPY amount, must reach the 3rd argument).
PROP-CEO-009 (m3修正, REQ-CEO-032): should_scale_down 3-way branch + the m3 disproof
(consecutive_bad_weeks survives build_next_registry's non-destructive merge).

ceo/allocator.py does not exist yet -> ImportError -> RED.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from allocator import (  # noqa: E402  RED: does not exist yet
    build_next_registry,
    capital_increase_within_realized_profit,
    realized_profit_usd,
    should_scale_down,
)

P = 0
F = 0


def chk(name, got, want):
    global P, F
    if got == want:
        print(f"  ok {name} ({got})")
        P += 1
    else:
        print(f"  FAIL {name} want={want} got={got}")
        F += 1


def chk_true(name, cond):
    chk(name, bool(cond), True)


# ---------- PROP-CEO-007: capital_increase_within_realized_profit ----------
chk(
    "capital gate: increase 50 (100-50) <= realized_profit 60 -> True",
    capital_increase_within_realized_profit(new_cap=100, old_cap=50, realized_profit_usd=60),
    True,
)
chk(
    "capital gate: increase 50 (100-50) > realized_profit 30 -> False",
    capital_increase_within_realized_profit(new_cap=100, old_cap=50, realized_profit_usd=30),
    False,
)

# M4 disproof: JPY-denominated loop (gig/affiliate), raw 9000 JPY @150 -> 60.0 USD. The GATE must
# receive this 60.0, never the raw 9000 (which would make the gate ~150x too permissive).
fx = {"jpy_usd_rate": 150.0}
jpy_entries = [{"amount": 0, "currency": "usd"}, {"amount": 9000, "currency": "jpy"}]
converted_profit = realized_profit_usd(jpy_entries, fx)
chk("M4: realized_profit_usd(9000 JPY @150) -> 60.0 USD (the value the gate must receive)", converted_profit, 60.0)
gate_result_correct = capital_increase_within_realized_profit(new_cap=100, old_cap=50, realized_profit_usd=converted_profit)
chk("M4: capital gate with the CONVERTED 60.0 -> True (increase 50 <= 60)", gate_result_correct, True)
chk_true("M4: the raw 9000 JPY figure was not what reached the gate (60.0 != 9000)", converted_profit != 9000)

# ---------- PROP-CEO-009: should_scale_down 3-way branch ----------
chk(
    "should_scale_down: score=0, beats=False, consecutive_bad_weeks=1 -> 'reduce_frequency'",
    should_scale_down(weekly_score=0, beats_previous_week=False, consecutive_bad_weeks=1),
    "reduce_frequency",
)
chk(
    "should_scale_down: consecutive_bad_weeks=2 (2-week threshold met) -> 'pause'",
    should_scale_down(weekly_score=0, beats_previous_week=False, consecutive_bad_weeks=2),
    "pause",
)
chk(
    "should_scale_down: score=10, beats=True -> 'none' (healthy loop)",
    should_scale_down(weekly_score=10, beats_previous_week=True, consecutive_bad_weeks=0),
    "none",
)

# m3 disproof: consecutive_bad_weeks lives in loop-registry.json's per-loop "consecutive_bad_weeks"
# subkey and MUST survive build_next_registry's non-destructive merge even when this pass's
# allocation_decisions doesn't touch that loop at all.
existing_registry = {"gig": {"fleet": 2, "allocation": {"x": 1}, "consecutive_bad_weeks": 1}}
next_registry = build_next_registry(
    existing_registry=existing_registry,
    budget_snapshot_by_loop={},
    rollback_restore=None,
    allocation_decisions={},  # this pass made no decision at all for "gig"
)
chk_true("m3: consecutive_bad_weeks key survives an untouched build_next_registry pass", "consecutive_bad_weeks" in next_registry.get("gig", {}))
chk("m3: consecutive_bad_weeks value (1) is preserved unchanged", next_registry["gig"]["consecutive_bad_weeks"], 1)

# and when allocation_decisions DOES update it for this loop, the new value wins.
next_registry2 = build_next_registry(
    existing_registry=existing_registry,
    budget_snapshot_by_loop={},
    rollback_restore=None,
    allocation_decisions={"gig": {"allocation": {"x": 2}, "consecutive_bad_weeks": 2}},
)
chk("m3: allocation_decisions with a new consecutive_bad_weeks value overrides the old one", next_registry2["gig"]["consecutive_bad_weeks"], 2)

print(f"=== test_capital_gate_and_scale_down: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
