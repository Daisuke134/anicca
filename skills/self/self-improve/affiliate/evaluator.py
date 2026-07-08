#!/usr/bin/env python3
"""affiliate/evaluator.py — affiliate loop evaluator (REQ-LV-110), copy+tweak of the clip evaluator
for the affiliate metrics ledger (~/.cloak/affiliate-metrics.jsonl). combined_score = views weight
+ commission earn weight (design spec's EDD table). Reads its ledger read-only; deterministic; no
LLM judge. Sandbox boundary: never imports anything that posts, applies, dispatches, or drives a
live web session.
"""
import os
import sys

_LIB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from ledger_metrics import evaluate_stage1_generic  # noqa: E402


def evaluate_stage1(ledger_path, config=None):
    return evaluate_stage1_generic(ledger_path, view_weight=1.0, earn_weight=1.0)
