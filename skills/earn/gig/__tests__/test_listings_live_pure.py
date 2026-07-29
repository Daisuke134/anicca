"""test_listings_live_pure.py — RED (Phase 2a, feature gig-feasibility-volume).
Purity Boundary Map (verification-architecture.md §1) — `funnel_report.py`'s `listings_live` count
is "the dedupe-by-`listing_id` + filter-`status=='live'` logic, factored to take an in-memory row
list" — the SAME "factor the pure compute out from the file read" pattern as `listings_due`.

Design contract this test locks in: `dedupe_latest_status` is widened with an optional `key_field`
parameter (default `"requestId"`, fully backward-compatible with every existing caller/test in
test_dedupe.py, which stays untouched and green) so it can ALSO dedupe by `listing_id` — reused, not
duplicated (Purity Boundary Map row 14: "reused for `listing_id` dedupe too"). A new
`funnel.count_live_listings(listing_rows)` pure function dedupes-latest-by-`listing_id` then counts
rows whose `status == "live"`.

`funnel.py`'s `dedupe_latest_status` does not accept `key_field` yet, and `count_live_listings` does
not exist yet -> TypeError/AttributeError -> RED.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import funnel  # noqa: E402

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


# --- dedupe_latest_status widened to accept key_field="listing_id" ---------------------------
listing_rows = [
    {"listing_id": "L1", "status": "live", "price_jpy": 8000},
    {"listing_id": "L1", "status": "live", "price_jpy": 9000},  # price update, same id, later row
    {"listing_id": "L2", "status": "live", "price_jpy": 5000},
]
deduped = funnel.dedupe_latest_status(listing_rows, key_field="listing_id")  # RED: no key_field param yet
chk("dedupe_latest_status(key_field='listing_id'): 3 rows, 2 distinct ids -> 2 rows kept",
    len(deduped), 2)
chk("dedupe_latest_status(key_field='listing_id'): kept L1 row is the LATEST (price_jpy=9000)",
    next(r["price_jpy"] for r in deduped if r["listing_id"] == "L1"), 9000)

# Backward-compat: default key_field still behaves exactly as before (requestId).
old_style_rows = [{"requestId": "R1", "status": "applied"}, {"requestId": "R1", "status": "replied"}]
chk("dedupe_latest_status default key_field is still 'requestId' (backward-compat)",
    len(funnel.dedupe_latest_status(old_style_rows)), 1)

# --- count_live_listings pure function --------------------------------------------------------
count_live = funnel.count_live_listings  # RED: AttributeError, does not exist yet

chk("count_live_listings([]) -> 0", count_live([]), 0)
chk("count_live_listings(None) -> 0", count_live(None), 0)

rows = [
    {"listing_id": "L1", "status": "live"},
    {"listing_id": "L2", "status": "live"},
    {"listing_id": "L3", "status": "delisted"},
    {"listing_id": "L1", "status": "delisted"},  # L1's LATEST status is delisted, must not count
]
chk("count_live_listings: dedupes by listing_id first, then counts status=='live' (L1 delisted later, only L2 counts)",
    count_live(rows), 1)

rows_no_id = [{"status": "live"}]  # missing listing_id -> excluded, never crashes
chk("count_live_listings: a row missing listing_id is excluded, never crashes",
    count_live(rows_no_id), 0)

print(f"=== test_listings_live_pure: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
