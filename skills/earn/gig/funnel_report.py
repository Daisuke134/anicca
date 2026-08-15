#!/usr/bin/env python3
"""funnel_report.py — REQ-LV-015 wiring: reads ~/gig/applied.jsonl (real CloakBrowser-collected
rows), dedupes to one row per requestId (F-VERIF-5 fix via funnel.dedupe_latest_status), summarizes
via the frozen summarize_gig_funnel, and appends ONE {ts, pass_id, applied, replied, won, paid,
by_category, listings_live} row to ~/gig/gig-funnel.jsonl. This is the SAME path
skills/self/cadence-evidence.py already reads via its GIG_FUNNEL_PATH override default (REQ-LV-
100/104 cadence contract for gig) — so once this script runs at the end of a real pass, the gig
cadence contract has real evidence to evaluate.

REQ-GFV-012 (additive schema change): `by_category` (dict, from funnel.summarize_gig_funnel_by_
category) and `listings_live` (int, from funnel.count_live_listings reading ~/gig/listings.jsonl)
are added alongside the EXISTING top-level applied/replied/won/paid keys — old consumers reading
only the top-level keys are unaffected.

CLI: python3 funnel_report.py [--pass-id ID] [--applied-path PATH] [--listings-path PATH] [--out-path PATH]
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from funnel import (  # noqa: E402
    count_live_listings,
    dedupe_latest_status,
    summarize_gig_funnel,
    summarize_gig_funnel_by_category,
)

DEFAULT_APPLIED = os.path.expanduser("~/gig/applied.jsonl")
DEFAULT_LISTINGS = os.path.expanduser("~/gig/listings.jsonl")
DEFAULT_OUT = os.path.expanduser("~/gig/gig-funnel.jsonl")


def _read_jsonl(path):
    rows = []
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def run(applied_path=DEFAULT_APPLIED, listings_path=DEFAULT_LISTINGS, out_path=DEFAULT_OUT, pass_id=None):
    rows = _read_jsonl(applied_path)
    deduped = dedupe_latest_status(rows)
    summary = summarize_gig_funnel(deduped)
    by_category = summarize_gig_funnel_by_category(deduped)
    listing_rows = _read_jsonl(listings_path)
    listings_live = count_live_listings(listing_rows)
    record = {
        "ts": int(time.time()),
        "pass_id": pass_id,
        **summary,
        "by_category": by_category,
        "listings_live": listings_live,
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pass-id", default=None)
    ap.add_argument("--applied-path", default=DEFAULT_APPLIED)
    ap.add_argument("--listings-path", default=DEFAULT_LISTINGS)
    ap.add_argument("--out-path", default=DEFAULT_OUT)
    a = ap.parse_args()
    print(json.dumps(
        run(a.applied_path, a.listings_path, a.out_path, a.pass_id), ensure_ascii=False
    ))
