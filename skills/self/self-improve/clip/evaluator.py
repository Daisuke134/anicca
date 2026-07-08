#!/usr/bin/env python3
"""clip/evaluator.py — clip loop evaluator (REQ-LV-110), copy+tweak of
~/anicca/skills/earn/self-improve/evaluator.py's evaluate_stage1 pattern for the clip loop's own
metrics ledger (CLIP_LEDGER). combined_score = mean views/reel (48h window, computed by the
caller when it builds the ledger rows it hands in) + payout USDC (design spec's EDD table). Reads
its ledger read-only; deterministic; no LLM judge (Verifier's Law). Sandbox boundary: this module
never imports anything that posts, applies, dispatches, or drives a live web session.
"""
import os
import sys

_LIB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from ledger_metrics import evaluate_stage1_generic  # noqa: E402


def evaluate_stage1(ledger_path, config=None):
    return evaluate_stage1_generic(ledger_path, view_weight=1.0, earn_weight=1.0)
