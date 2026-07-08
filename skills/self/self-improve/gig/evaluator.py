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
