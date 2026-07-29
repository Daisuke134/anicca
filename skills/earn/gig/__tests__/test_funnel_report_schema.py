"""test_funnel_report_schema.py — RED (Phase 2a, feature gig-feasibility-volume).
PROP-014 / REQ-GFV-012 — a `gig-funnel.jsonl` row written by `funnel_report.run()` (a) keeps the
EXISTING top-level shape `{ts,pass_id,applied,replied,won,paid}` unchanged AND (b) adds `by_category`
(dict, from PROP-012's `summarize_gig_funnel_by_category`) AND (c) adds `listings_live` (int, from
the new dedupe-by-listing_id + filter-status=='live' count) — read from a NEW `listings.jsonl` path
argument.

Design contract this test locks in: `funnel_report.run()` gains a `listings_path=` kwarg (additive,
defaults to `~/gig/listings.jsonl`) — existing callers passing only `applied_path`/`out_path`/
`pass_id` keep working unmodified.

`funnel_report.run()` does not accept `listings_path` and does not add `by_category`/`listings_live`
to its returned record yet -> TypeError / KeyError -> RED.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import funnel_report  # noqa: E402

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


tmp = tempfile.mkdtemp()
applied_path = os.path.join(tmp, "applied.jsonl")
listings_path = os.path.join(tmp, "listings.jsonl")
out_path = os.path.join(tmp, "gig-funnel.jsonl")

with open(applied_path, "w") as f:
    f.write(json.dumps({"requestId": "R1", "status": "applied", "category": "PPT/スライド"}) + "\n")
    f.write(json.dumps({"requestId": "R2", "status": "検収完了", "category": "資料作成"}) + "\n")

with open(listings_path, "w") as f:
    f.write(json.dumps({"listing_id": "L1", "status": "live"}) + "\n")
    f.write(json.dumps({"listing_id": "L2", "status": "delisted"}) + "\n")

record = funnel_report.run(
    applied_path=applied_path, listings_path=listings_path, out_path=out_path, pass_id="p-test"
)  # RED: run() does not accept listings_path yet

chk("record keeps existing top-level keys: ts present", "ts" in record, True)
chk("record keeps existing top-level keys: pass_id preserved", record["pass_id"], "p-test")
chk("record keeps existing top-level keys: applied/replied/won/paid present (int)",
    all(k in record for k in ("applied", "replied", "won", "paid")), True)
chk("record adds by_category (dict)", isinstance(record.get("by_category"), dict), True)
chk("record's by_category has the PPT/スライド bucket with applied=1",
    record.get("by_category", {}).get("PPT/スライド", {}).get("applied"), 1)
chk("record adds listings_live (int) = 1 (only L1 is live, L2 delisted)",
    record.get("listings_live"), 1)

# Edge case: listings.jsonl absent -> listings_live:0, never crash.
out_path2 = os.path.join(tmp, "gig-funnel2.jsonl")
missing_listings_path = os.path.join(tmp, "does-not-exist-listings.jsonl")
record2 = funnel_report.run(
    applied_path=applied_path, listings_path=missing_listings_path, out_path=out_path2, pass_id="p2"
)
chk("listings.jsonl absent -> listings_live:0, no crash", record2.get("listings_live"), 0)

# Written line on disk must itself be the schema-complete record (append behavior unchanged).
with open(out_path) as f:
    last_line = json.loads([ln for ln in f if ln.strip()][-1])
chk("the appended gig-funnel.jsonl line on disk also carries by_category + listings_live",
    ("by_category" in last_line and "listings_live" in last_line), True)

print(f"=== test_funnel_report_schema: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
