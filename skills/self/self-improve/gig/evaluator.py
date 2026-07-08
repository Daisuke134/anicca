#!/usr/bin/env python3
"""gig/evaluator.py — gig loop evaluator (REQ-LV-110), copy+tweak of the clip evaluator for the gig
funnel ledger (~/gig/gig-funnel.jsonl). Metric (design spec's EDD table): funnel — 応募→返信率→
受注率→入金JPY/週. When a row carries funnel counts (applied/replied/won/paid, REQ-LV-015 shape)
those drive the score; otherwise falls back to the shared generic views/earn scoring so this
evaluator degrades gracefully on a plain metrics ledger too. Reads its ledger read-only;
deterministic; no LLM judge. Sandbox boundary: never imports anything that posts, applies,
dispatches, or drives a live web session.
"""
import os
import sys

_LIB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from ledger_metrics import evaluate_stage1_generic, load_ledger_rows  # noqa: E402


def _funnel_score(rows):
    applied = sum(int(r.get("applied") or 0) for r in rows)
    replied = sum(int(r.get("replied") or 0) for r in rows)
    won = sum(int(r.get("won") or 0) for r in rows)
    paid_jpy = sum(float(r.get("paid_jpy") or r.get("earn_jpy") or 0) for r in rows)
    reply_rate = (replied / applied) if applied else 0.0
    win_rate = (won / replied) if replied else 0.0
    return reply_rate + win_rate + paid_jpy


def evaluate_stage1(ledger_path, config=None):
    rows = load_ledger_rows(ledger_path)
    has_funnel_shape = any(("applied" in r or "won" in r) for r in rows)
    if has_funnel_shape:
        return {"combined_score": _funnel_score(rows), "rows_evaluated": len(rows)}
    return evaluate_stage1_generic(ledger_path, view_weight=1.0, earn_weight=1.0)


def evaluate_by_category(gig_funnel_rows):
    """REQ-GFV-013 (PROP-018) — read-only, deterministic: given `gig-funnel.jsonl` row dicts
    (already parsed, in-memory — no file I/O here), aggregates each row's `by_category` block
    (REQ-GFV-012) across the input rows, returning `{category: {reply_rate, win_rate, paid_jpy}}`.
    Rows lacking `by_category` (older, pre-this-feature rows) contribute zero to every category's
    tally without raising — never crashes on a mixed-schema ledger. Additive only: does not modify
    or replace `evaluate_stage1`'s existing whole-pass scoring. Sandbox boundary: imports nothing
    that posts, applies, dispatches, or drives a live web session."""
    totals = {}
    for row in gig_funnel_rows or []:
        by_category = (row or {}).get("by_category") or {}
        for category, bucket in by_category.items():
            bucket = bucket or {}
            t = totals.setdefault(category, {"applied": 0, "replied": 0, "won": 0, "paid_jpy": 0.0})
            t["applied"] += int(bucket.get("applied") or 0)
            t["replied"] += int(bucket.get("replied") or 0)
            t["won"] += int(bucket.get("won") or 0)
            t["paid_jpy"] += float(bucket.get("paid_jpy") or bucket.get("earn_jpy") or 0)

    result = {}
    for category, t in totals.items():
        reply_rate = (t["replied"] / t["applied"]) if t["applied"] else 0.0
        win_rate = (t["won"] / t["replied"]) if t["replied"] else 0.0
        result[category] = {
            "reply_rate": reply_rate,
            "win_rate": win_rate,
            "paid_jpy": t["paid_jpy"],
        }
    return dict(sorted(result.items(), key=lambda kv: kv[1]["paid_jpy"], reverse=True))
