#!/usr/bin/env python3
"""gig_funnel.py — deterministic funnel-metrics writer for the gig earn-core (gig L1-c).

Called once per cron pass (after EARNED CHECK, before the B4 improve step). Reads the
ground-truth jsonl files the core writes and appends ONE funnel snapshot row to
~/gig/gig-funnel.jsonl, both overall and broken down by_category. This is the persisted,
per-pass source of truth that the 50/50 self-improve EVAL step (gig L1-b) compares
experiments against — replacing the ad-hoc inline recompute so trends survive across passes.

Schema is CONTINUOUS with the pre-existing (orphaned) gig-funnel.jsonl rows so historical
data still reads cleanly:
  {ts, pass_id, applied, replied, won, paid, jpy, listings_live, by_category:{<cat>:{applied,replied,won,paid}}}

Counting rules (deterministic, no judgment):
  applied  = ~/gig/applied.jsonl rows with status == "applied"
  replied  = ~/gig/applied.jsonl rows with status in {replied, 評価依頼, delivered}
  won      = ~/gig/lessons.jsonl rows with outcome == "accepted"
  paid     = ~/gig/earnings.jsonl rows with a SETTLED status AND evidence AND jpy>0
  jpy      = sum of jpy over those settled earnings rows
  listings_live = distinct service_id in ~/gig/shuppin.jsonl that ever had a
                  shuppin_published action (fallback: distinct service_id seen)

Category for an applied row: row.category if present, else joined from lessons.jsonl by
requestId, else "uncategorized".

Exit 0 always: any error still appends a minimal valid row (with _error) and never aborts
the pass. Prints the written row as one JSON line to stdout.
"""
import json
import os
import sys
import time

HOME = os.path.expanduser("~")
GIG_DIR = os.path.join(HOME, "gig")
FUNNEL_FILE = os.path.join(GIG_DIR, "gig-funnel.jsonl")

SETTLED = {"検収", "支払", "検収完了", "completed", "paid"}
REPLIED_STATUS = {"replied", "評価依頼", "delivered"}


def read_rows(name):
    """Read a jsonl file into a list of dicts; missing/corrupt lines are skipped."""
    path = os.path.join(GIG_DIR, name)
    out = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if isinstance(obj, dict):
                            out.append(obj)
                    except (json.JSONDecodeError, ValueError):
                        continue
        except OSError:
            pass
    return out


def jnum(v):
    try:
        return float(str(v).replace(",", "").replace("¥", "").replace("円", "").strip() or 0)
    except (ValueError, TypeError):
        return 0.0


def blank_cat():
    return {"applied": 0, "replied": 0, "won": 0, "paid": 0}


def build_funnel(pass_id):
    applied_rows = read_rows("applied.jsonl")
    lessons = read_rows("lessons.jsonl")
    earnings = read_rows("earnings.jsonl")
    shuppin = read_rows("shuppin.jsonl")

    # requestId -> category from lessons (fallback join for applied rows lacking category)
    cat_by_req = {}
    for l in lessons:
        rid = l.get("requestId")
        cat = l.get("category")
        if rid is not None and cat:
            cat_by_req[str(rid)] = cat

    by_cat = {}

    def bump(cat, key):
        cat = cat or "uncategorized"
        by_cat.setdefault(cat, blank_cat())[key] += 1

    applied = replied = 0
    for r in applied_rows:
        status = r.get("status")
        cat = r.get("category") or cat_by_req.get(str(r.get("requestId"))) or "uncategorized"
        if status == "applied":
            applied += 1
            bump(cat, "applied")
        elif status in REPLIED_STATUS:
            replied += 1
            bump(cat, "replied")

    # won = accepted outcomes from lessons
    won = 0
    for l in lessons:
        if l.get("outcome") == "accepted":
            won += 1
            bump(l.get("category") or "uncategorized", "won")

    # paid + jpy = settled earnings with evidence
    paid = 0
    jpy = 0.0
    for e in earnings:
        if e.get("status") in SETTLED and e.get("evidence") and jnum(e.get("jpy", 0)) > 0:
            paid += 1
            jpy += jnum(e.get("jpy", 0))
            cat = cat_by_req.get(str(e.get("requestId"))) or "uncategorized"
            bump(cat, "paid")

    # listings_live = distinct service_id ever published (fallback: distinct seen)
    published_ids = set()
    seen_ids = set()
    for s in shuppin:
        sid = s.get("service_id")
        if sid is None:
            continue
        seen_ids.add(str(sid))
        if s.get("action") == "shuppin_published":
            published_ids.add(str(sid))
    listings_live = len(published_ids) if published_ids else len(seen_ids)

    return {
        "ts": int(time.time()),
        "pass_id": pass_id,
        "applied": applied,
        "replied": replied,
        "won": won,
        "paid": paid,
        "jpy": round(jpy, 0),
        "listings_live": listings_live,
        "by_category": by_cat,
    }


def main():
    pass_id = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else None
    try:
        row = build_funnel(pass_id)
    except Exception as exc:  # never abort the pass
        row = {"ts": int(time.time()), "pass_id": pass_id, "applied": 0, "replied": 0,
               "won": 0, "paid": 0, "jpy": 0, "listings_live": 0, "by_category": {},
               "_error": str(exc)}
        print(f"gig_funnel.py ERROR: {exc}", file=sys.stderr)
    try:
        os.makedirs(GIG_DIR, exist_ok=True)
        with open(FUNNEL_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError as exc:
        print(f"gig_funnel.py write ERROR: {exc}", file=sys.stderr)
    print(json.dumps(row, ensure_ascii=False))


if __name__ == "__main__":
    main()
