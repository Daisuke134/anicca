"""test_currency_conversion.py — RED (Phase 2a, feature claude-p-ceo-loop).
PROP-CEO-013 (M1/M3修正, REQ-CEO-002(c)/050/051): sum_earn_by_currency + convert_to_usd +
realized_profit_usd + company_score (loop-cross-cutting USD conversion, INV-CEO-1's single shared
conversion path) + build_verification_row (10-field canonical row, m5修正).

ceo/allocator.py does not exist yet -> ImportError -> RED.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from allocator import (  # noqa: E402  RED: does not exist yet
    build_verification_row,
    company_score,
    convert_to_usd,
    realized_profit_usd,
    sum_earn_by_currency,
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


# ---------- sum_earn_by_currency: always 2 entries, no fallback-field-winner branching ----------
rows = [{"earn_usdc": 5.0}, {"earn_jpy": 1000}, {"commission_jpy": 500}]
entries = sum_earn_by_currency(rows)
chk("sum_earn_by_currency: always returns exactly 2 entries", len(entries), 2)
usd_entry = next(e for e in entries if e["currency"] == "usd")
jpy_entry = next(e for e in entries if e["currency"] == "jpy")
chk("sum_earn_by_currency: usd entry = sum(earn_usdc) only = 5.0", usd_entry["amount"], 5.0)
chk("sum_earn_by_currency: jpy entry = sum(earn_jpy)+sum(commission_jpy) = 1000+500 = 1500", jpy_entry["amount"], 1500)

empty_entries = sum_earn_by_currency([])
chk("sum_earn_by_currency: empty rows -> still 2 entries, both amount 0 (never crashes)", len(empty_entries), 2)
chk_true("sum_earn_by_currency: empty rows -> all amounts are 0", all(e["amount"] == 0 for e in empty_entries))

# ---------- convert_to_usd: identity for usd, division by jpy_usd_rate for jpy ----------
fx = {"jpy_usd_rate": 150.0}
chk("convert_to_usd(150, 'jpy', rate=150.0) -> 1.0", convert_to_usd(150, "jpy", fx), 1.0)
chk("convert_to_usd(5.0, 'usd', ...) -> 5.0 (no conversion)", convert_to_usd(5.0, "usd", fx), 5.0)

# ---------- realized_profit_usd: sums convert_to_usd(entry) over an arbitrary-length entries list ----------
chk(
    "realized_profit_usd([usd 5.0, jpy 1500] @150) -> 5.0 + 10.0 = 15.0",
    realized_profit_usd([{"amount": 5.0, "currency": "usd"}, {"amount": 1500, "currency": "jpy"}], fx),
    15.0,
)

# ---------- company_score: loop-cross-cutting sum of realized_profit_usd, JPY never leaks unconverted ----------
per_loop = {
    "clip": [{"amount": 5.0, "currency": "usd"}],
    "gig": [{"amount": 0, "currency": "usd"}, {"amount": 1500, "currency": "jpy"}],
}
score = company_score(per_loop, fx)
chk("company_score: clip(5.0 usd) + gig(1500 jpy -> 10.0 usd) = 15.0", score, 15.0)
chk_true("company_score: the raw 1500 JPY figure never appears unconverted in the total", score != 1505.0)
chk("company_score: empty roster -> 0.0 (never crashes)", company_score({}, fx), 0.0)

# ---------- build_verification_row: canonical single-row shape, all 10 fields ----------
row = build_verification_row(
    ts="2026-07-06T09:00:00Z",
    week_start="2026-06-29",
    prev=10.0,
    this=15.0,
    beats=True,
    alloc_ref="loop-registry.json@2026-07-06",
    consecutive_miss_count=0,
    cooldown_weeks_remaining=0,
    rollback_fired=False,
    rolled_back_to_week=None,
)
expected_keys = {
    "ts", "week_start", "prev_week_company_score", "this_week_company_score",
    "beats_previous_week", "allocation_change_ref", "consecutive_miss_count",
    "cooldown_weeks_remaining", "rollback_fired", "rolled_back_to_week",
}
chk_true("build_verification_row: all 10 canonical fields present", expected_keys <= set(row.keys()))
chk("build_verification_row: this_week_company_score set correctly", row["this_week_company_score"], 15.0)
chk("build_verification_row: beats_previous_week set correctly", row["beats_previous_week"], True)
chk("build_verification_row: non-rollback pass -> rolled_back_to_week is None", row["rolled_back_to_week"], None)

row_rollback = build_verification_row(
    ts="2026-07-13T09:00:00Z", week_start="2026-07-06", prev=5.0, this=3.0, beats=False,
    alloc_ref="loop-registry.json@2026-07-13", consecutive_miss_count=0, cooldown_weeks_remaining=1,
    rollback_fired=True, rolled_back_to_week="2026-06-22",
)
chk("build_verification_row: rollback-fired pass carries rolled_back_to_week", row_rollback["rolled_back_to_week"], "2026-06-22")
chk("build_verification_row: rollback-fired pass records rollback_fired=True", row_rollback["rollback_fired"], True)

print(f"=== test_currency_conversion: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
