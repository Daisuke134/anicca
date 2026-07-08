#!/usr/bin/env python3
"""bounty/evaluator.py — bounty loop evaluator (REQ-LV-110), copy+tweak of the clip evaluator for
the bounty funnel ledger (bounty-funnel.jsonl). When a row carries funnel counts (checked/
survivors/claimed/submitted, REQ-LV-016 shape) those drive the score (submission rate + confirmed
USDC earn); otherwise falls back to the shared generic views/earn scoring. Reads its ledger
read-only; deterministic; no LLM judge. Sandbox boundary: never imports anything that posts,
applies, dispatches, or drives a live web session.
"""
import os
import sys

_LIB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from ledger_metrics import evaluate_stage1_generic, load_ledger_rows  # noqa: E402


def _funnel_score(rows):
    checked = sum(int(r.get("checked") or 0) for r in rows)
    submitted = sum(int(r.get("submitted") or 0) for r in rows)
    earn_usdc = sum(float(r.get("earn_usdc") or 0) for r in rows)
    submit_rate = (submitted / checked) if checked else 0.0
    return submit_rate + earn_usdc


def evaluate_stage1(ledger_path, config=None):
    rows = load_ledger_rows(ledger_path)
    has_funnel_shape = any(("checked" in r or "submitted" in r) for r in rows)
    if has_funnel_shape:
        return {"combined_score": _funnel_score(rows), "rows_evaluated": len(rows)}
    return evaluate_stage1_generic(ledger_path, view_weight=1.0, earn_weight=1.0)
