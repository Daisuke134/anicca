#!/usr/bin/env python3
"""clip/evaluator.py — clip loop evaluator (REQ-LV-110), copy+tweak of
__REPO_ROOT__/skills/earn/self-improve/evaluator.py's evaluate_stage1 pattern for the clip loop's own
metrics ledger (CLIP_LEDGER). combined_score = mean views/reel (48h window, computed by the
caller when it builds the ledger rows it hands in) + payout USDC (design spec's EDD table) MINUS
a small quality penalty for posted clips recorded below the resolution/bitrate floor in
clip-metrics.jsonl (2026-07-10 quality self-heal incident: posted files measured 202x360 @
~200kbps despite 720p/1080p sources existing for the same video id). Reads both ledgers
read-only; deterministic; no LLM judge (Verifier's Law). Sandbox boundary: this module never
imports anything that posts, applies, dispatches, or drives a live web session.
"""
import json
import os
import sys

_LIB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from ledger_metrics import evaluate_stage1_generic  # noqa: E402

# Small additive penalty per posted clip recorded below the quality floor (see
# __REPO_ROOT__/skills/earn/clip/verify_posted_quality.py for how below_floor rows are produced).
# Kept small and additive so it never dominates the existing view/earn weights -- it nudges
# scoring, it does not override it.
QUALITY_PENALTY_PER_ROW = 50.0
DEFAULT_METRICS_PATH = os.path.expanduser("~/.local/state/life-manager/state/clip-metrics.jsonl")


def _count_below_floor(metrics_path):
    """Read-only. Counts below_floor:true rows in clip-metrics.jsonl. Missing/unreadable
    file -> 0, never raises (an evaluator must never block the loop)."""
    count = 0
    try:
        with open(metrics_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("below_floor"):
                    count += 1
    except FileNotFoundError:
        pass
    return count


def evaluate_stage1(ledger_path, config=None):
    config = config or {}
    metrics_path = config.get("metrics_path", DEFAULT_METRICS_PATH)
    result = evaluate_stage1_generic(ledger_path, view_weight=1.0, earn_weight=1.0)
    below_floor_rows = _count_below_floor(metrics_path)
    quality_penalty = QUALITY_PENALTY_PER_ROW * below_floor_rows
    result["combined_score"] = result["combined_score"] - quality_penalty
    result["below_floor_rows"] = below_floor_rows
    result["quality_penalty"] = quality_penalty
    return result
