#!/usr/bin/env python3
"""
B7 — conversion attribution (deterministic TOOL, conservative by design).

Joins the X marketing posts (x-ledger: agent_id + post date) against Capafy sales
(capafy-earn-ledger.jsonl, mirrored by capafy_earn_reconcile.py) and records, per post,
whether ANY sale fell within a 7-day window AFTER the post.

★ HONEST LIMIT: Capafy's sales/trend is a PER-DAY AGGREGATE (orders/gross_usd) with NO
per-listing granularity — the ledger cannot say WHICH listing sold. So this NEVER asserts
"this post drove this sale"; it only flags a date-window CANDIDATE for a human/reflect to weigh.
UTM (utm_medium=x_reply) is written into the click URL so that once Capafy exposes per-listing
or per-UTM sales data, this join can tighten. Until then: candidate signal, not proof.

Appends candidates to `capafy-attribution.jsonl`. If no sale falls in any window, that is a
clean, correct no-op (sales are currently ~0).
"""
import datetime, json, os, sys, time

XLEDGER = os.path.expanduser("~/.openclaw/state/capafy-marketing-x-ledger.jsonl")
EARN = os.path.expanduser("~/anicca/skills/self/capafy-loop/state/capafy-earn-ledger.jsonl")
ATTR = os.path.expanduser("~/.openclaw/state/capafy-attribution.jsonl")
WINDOW_DAYS = 7


def _date(ts):
    return datetime.datetime.fromtimestamp(int(ts), datetime.timezone(datetime.timedelta(hours=9))).date()


def _load(path):
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


def main():
    posts = [r for r in _load(XLEDGER) if r.get("mode") == "live_browser" and r.get("ts")]
    # sale-days with real orders
    sales = []
    for r in _load(EARN):
        if r.get("orders") and int(r.get("orders", 0)) > 0 and r.get("date"):
            try:
                sales.append((datetime.date.fromisoformat(r["date"]), int(r["orders"]), r.get("gross_usd", 0)))
            except Exception:
                continue

    seen = {json.dumps({"a": c.get("agent_id"), "p": c.get("post_date"), "s": c.get("sale_date")}, sort_keys=True)
            for c in _load(ATTR)}
    candidates = 0
    os.makedirs(os.path.dirname(ATTR), exist_ok=True)
    for p in posts:
        pd = _date(p["ts"])
        for sale_date, orders, gross in sales:
            if pd <= sale_date <= pd + datetime.timedelta(days=WINDOW_DAYS):
                row = {"ts": int(time.time()), "agent_id": p.get("agent_id"),
                       "listing_name": p.get("listing_name"), "post_date": pd.isoformat(),
                       "sale_date": sale_date.isoformat(), "orders": orders, "gross_usd": gross,
                       "confidence": "candidate",
                       "note": "date-window match only; Capafy sales are per-day aggregate (no per-listing/UTM granularity) — NOT proof this listing sold"}
                key = json.dumps({"a": row["agent_id"], "p": row["post_date"], "s": row["sale_date"]}, sort_keys=True)
                if key in seen:
                    continue
                with open(ATTR, "a") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                seen.add(key)
                candidates += 1
    print(json.dumps({"ok": True, "posts": len(posts), "sale_days": len(sales),
                      "new_candidates": candidates,
                      "note": "no candidate = correct when no sale falls within 7d of a post (sales ~0 today)"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
