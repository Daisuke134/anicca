"""test_gig_activity_event_dates.py — RED (Phase 2a, feature gig-feasibility-volume).
PROP-030 / REQ-GFV-022 (rewritten, spec-review iteration-2 BLOCKING-1 fix) — a pure function in
`cadence-evidence.py` computing `event_dates` = union of (a) JST dates of `applied_rows` entries
whose `status` is EXACTLY `"applied"`, `"replied"`, or in `_WON_STATUSES`/`_PAID_STATUSES` (a local
literal copy of funnel.py's vocabulary, since funnel.py lives in a different repo), and (b) the JST
date of each `listings_rows` entry's FIRST-EVER appearance for its `listing_id` (later price-updates
for an already-seen id do NOT contribute an additional date).

Design contract this test locks in:
    cadence_evidence._gig_activity_event_dates(applied_rows, listings_rows) -> set[str]

Deliberately uses an EXACT-MATCH filter (not `status.startswith("applied")`) — this session measured
a real `"applied_0"` status string (a zero-viable-candidates scan summary, NOT a real application)
that a naive prefix match would wrongly count as activity; this test proves the exact-match rule
excludes it.

`cadence-evidence.py` does not export `_gig_activity_event_dates` yet -> AttributeError -> RED.
"""
import importlib.util
import os
import sys

_SELF_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _SELF_DIR)
_spec = importlib.util.spec_from_file_location("cadence_evidence", os.path.join(_SELF_DIR, "cadence-evidence.py"))
CE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CE)

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


event_dates = CE._gig_activity_event_dates  # RED: AttributeError, does not exist yet

# --- Fixture 1: a day with one real "applied" row + three housekeeping rows -> day IS in event_dates
day1_rows = [
    {"ts": "2026-07-01T10:00:00Z", "status": "applied", "requestId": "R1"},   # +09:00 -> still 2026-07-01
    {"ts": "2026-07-01T11:00:00Z", "status": "no_action"},
    {"ts": "2026-07-01T12:00:00Z", "status": "0_new_applications_market_saturated"},
    {"ts": "2026-07-01T13:00:00Z", "status": "applied_0"},
]
dates1 = event_dates(day1_rows, [])
chk("Fixture 1: day with one real 'applied' row + 3 housekeeping rows -> day IS in event_dates",
    "2026-07-01" in dates1, True)

# --- Fixture 2: a day with ONLY housekeeping/non-exact-match rows -> day is NOT in event_dates
day2_rows = [
    {"ts": "2026-07-02T10:00:00Z", "status": "no_action"},
    {"ts": "2026-07-02T11:00:00Z", "status": "applied_0"},
    {"ts": "2026-07-02T12:00:00Z", "status": "action_taken"},
]
dates2 = event_dates(day2_rows, [])
chk("Fixture 2: day with ONLY housekeeping/non-exact-match rows -> day is NOT in event_dates",
    "2026-07-02" in dates2, False)

# --- Fixture 3: listings_rows day-1 creates L1, day-5 price-updates L1 -> only day-1 contributes
listings_rows = [
    {"ts": "2026-07-01T09:00:00Z", "listing_id": "L1", "status": "live", "price_jpy": 8000},
    {"ts": "2026-07-05T09:00:00Z", "listing_id": "L1", "status": "live", "price_jpy": 9000},  # price update, same id
]
dates3 = event_dates([], listings_rows)
chk("Fixture 3: listing_id L1 first-seen day-1 IS in event_dates",
    "2026-07-01" in dates3, True)
chk("Fixture 3: listing_id L1's LATER price-update day-5 does NOT add an additional date",
    "2026-07-05" in dates3, False)

# --- Fixture 4: absent/empty listings_rows -> contributes nothing, never crashes
dates4 = event_dates([], [])
chk("Fixture 4: empty applied_rows + empty listings_rows -> empty event_dates, no crash",
    dates4, set())
dates4b = event_dates([], None)
chk("Fixture 4b: None listings_rows -> no crash, contributes nothing",
    dates4b, set())

# --- Fixture 5: a listings row missing listing_id -> excluded, never crashes
listings_missing_id = [{"ts": "2026-07-03T09:00:00Z", "status": "live"}]
dates5 = event_dates([], listings_missing_id)
chk("Fixture 5: listings row missing listing_id -> excluded, no crash",
    dates5, set())

# --- won/paid statuses count too (_WON_STATUSES/_PAID_STATUSES local copy of funnel.py's vocabulary)
won_rows = [{"ts": "2026-07-04T09:00:00Z", "status": "受注", "requestId": "R2"}]
paid_rows = [{"ts": "2026-07-06T09:00:00Z", "status": "支払", "requestId": "R3"}]
chk("won status (受注) counts as real activity", "2026-07-04" in event_dates(won_rows, []), True)
chk("paid status (支払) counts as real activity", "2026-07-06" in event_dates(paid_rows, []), True)

# --- exact-match, not prefix-match: "applied_1"/"applied_2" summary rows must NOT count.
prefix_trap_rows = [
    {"ts": "2026-07-07T09:00:00Z", "status": "applied_1"},
    {"ts": "2026-07-07T10:00:00Z", "status": "applied_2"},
]
chk("EXACT-match rule (not startswith): 'applied_1'/'applied_2' summary rows do NOT count as activity",
    "2026-07-07" in event_dates(prefix_trap_rows, []), False)

print(f"=== test_gig_activity_event_dates: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
