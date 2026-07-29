"""test_listings_due_pure.py — RED (Phase 2a, feature gig-feasibility-volume).
PROP-006 / REQ-GFV-005 — the `listings_due` boolean-decision sub-logic, factored out to be pure
(callable with an in-memory row list + `now` timestamp, per verification-architecture.md §1's
Purity Boundary Map — the FILE READ that produces `listing_rows` is the effectful shell, tested
separately via subprocess in test_passprep_stdout_fields.mjs).

Design contract this test locks in:
    passprep.compute_listings_due(listing_rows, now_epoch, listing_weekly_target) -> bool
True WHEN the count of rows with `ts` within the trailing 7 days (relative to now_epoch) is BELOW
listing_weekly_target, else False. Malformed/missing `ts` rows are skipped, never crash (same
tolerant-parse convention as every other ledger reader in this codebase).

`passprep.py` does not export `compute_listings_due` yet -> ImportError -> RED.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import passprep  # noqa: E402  RED: compute_listings_due does not exist yet

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


NOW = 1783900000  # arbitrary fixed epoch, 2026-07-08-ish
DAY = 86400

chk("0 rows in trailing 7 days, target=2 -> listings_due:true",
    passprep.compute_listings_due([], NOW, 2), True)

chk("absent/empty listing_rows -> listings_due:true (bootstrap case)",
    passprep.compute_listings_due(None, NOW, 2), True)

rows_at_target = [
    {"ts": NOW - 1 * DAY, "listing_id": "L1"},
    {"ts": NOW - 3 * DAY, "listing_id": "L2"},
]
chk("exactly `target`(2) rows in trailing 7 days -> listings_due:false",
    passprep.compute_listings_due(rows_at_target, NOW, 2), False)

rows_below_target = [{"ts": NOW - 1 * DAY, "listing_id": "L1"}]
chk("1 row in trailing 7 days, target=2 -> listings_due:true (below target)",
    passprep.compute_listings_due(rows_below_target, NOW, 2), True)

rows_boundary = [{"ts": NOW - 6 * DAY, "listing_id": "L1"}]  # target-1 = 1 row -> still true
chk("boundary: target-1(1) rows in trailing 7 days, target=2 -> listings_due:true",
    passprep.compute_listings_due(rows_boundary, NOW, 2), True)

rows_outside_window = [{"ts": NOW - 8 * DAY, "listing_id": "L1"}]  # older than 7 days, doesn't count
chk("a row 8 days old (outside the 7-day window) does not count toward the target",
    passprep.compute_listings_due(rows_outside_window, NOW, 2), True)

rows_malformed = [{"listing_id": "L1"}, {"ts": "not-a-number", "listing_id": "L2"}, {"ts": NOW - DAY, "listing_id": "L3"}]
chk("malformed/missing ts rows are skipped (never crash, never miscounted)",
    passprep.compute_listings_due(rows_malformed, NOW, 2), True)  # only 1 valid row < target(2)

print(f"=== test_listings_due_pure: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
