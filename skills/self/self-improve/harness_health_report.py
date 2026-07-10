#!/usr/bin/env python3
"""harness_health_report.py -- anicca-harness-tooluse-health R8: thin CLI, the concrete surface a
self-improve consumer (or a future self-fix caller -- explicit FOLLOW-UP work, R10, not wired here)
reads. The ONLY caller of compute_harness_health against real disk state on the Python side.

CLI: python3 harness_health_report.py <ledger_path> [--threshold N]

Prints compute_harness_health's JSON to stdout. Neither this file nor lib/harness_health.py is
imported by, nor changes the return shape of, skills/earn/self-improve/evaluator.py or
skills/self/self-improve/weekly_report.py (R9) -- those operate on a disjoint domain (a frozen
backtest fixture; per-EDD-loop outcome ledgers) that does not contain wake-loop tool-call data.
"""
import argparse
import json
import os
import sys

SELF_IMPROVE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SELF_IMPROVE_DIR, "lib"))
from ledger_metrics import load_ledger_rows  # noqa: E402
from harness_health import compute_harness_health, DEFAULT_STREAK_THRESHOLD  # noqa: E402


def main(argv):
    parser = argparse.ArgumentParser(description="Print anicca-harness-tooluse-health's whole-ledger report as JSON.")
    parser.add_argument("ledger_path", help="path to a runtime/loop/index.mjs-produced ledger.jsonl")
    parser.add_argument("--threshold", type=int, default=DEFAULT_STREAK_THRESHOLD,
                         help=f"consecutive-failure-streak escalation threshold (default {DEFAULT_STREAK_THRESHOLD})")
    args = parser.parse_args(argv)

    rows = load_ledger_rows(args.ledger_path)
    report = compute_harness_health(rows, streak_threshold=args.threshold)
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
