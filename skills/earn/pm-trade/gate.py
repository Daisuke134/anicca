#!/usr/bin/env python3
"""gate.py — the REAL paper-pass producer (fixes the fake PM_PAPER_PASS env gate, adversary FIND-004).

A real order is allowed ONLY after the paper record proves the strategy: PM_PAPER_PASS is computed HERE
from resolved paper trades, never trusted from a bare env var. Pure `evaluate_gate` + a CLI that reads the
paper ledger and prints PASS/FAIL so run.sh consumes a produced value, not a spoofable one.
"""
import json
import os
import pathlib
import sys

LEDGER = pathlib.Path(os.path.expanduser("~/loops/earn-pm-trade/paper-positions.jsonl"))
MIN_RESOLVED = 20      # need a real sample, not one lucky trade
MIN_WINRATE = 0.55     # must beat coin-flip with margin
MIN_NET_USDC = 0.0     # paper P&L must be non-negative


def evaluate_gate(resolved, min_resolved=MIN_RESOLVED, min_winrate=MIN_WINRATE, min_net=MIN_NET_USDC):
    """resolved = list of {pnl_usdc: float} for RESOLVED paper trades. Returns (passed: bool, stats: dict).
    PASS iff enough resolved trades AND winrate >= threshold AND net paper P&L >= min_net. Pure."""
    n = len(resolved)
    if n < min_resolved:
        return (False, {"resolved": n, "reason": f"need >= {min_resolved} resolved paper trades"})
    wins = sum(1 for r in resolved if float(r.get("pnl_usdc", 0.0)) > 0.0)
    net = sum(float(r.get("pnl_usdc", 0.0)) for r in resolved)
    winrate = wins / n
    passed = (winrate >= min_winrate) and (net >= min_net)
    return (passed, {"resolved": n, "winrate": round(winrate, 4), "net_usdc": round(net, 4)})


def _load_resolved(ledger=LEDGER):
    rows = []
    if not ledger.exists():
        return rows
    for line in ledger.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        # ONLY momentum/decide.py rows (avoid colliding with pm-paper.py's different schema)
        if r.get("src") == "momentum" and r.get("status") == "resolved" and "pnl_usdc" in r:
            rows.append(r)
    return rows


if __name__ == "__main__":
    passed, stats = evaluate_gate(_load_resolved())
    # produce the value run.sh consumes: prints "PM_PAPER_PASS=1" or "=0" + stats to stderr
    print(f"PM_PAPER_PASS={1 if passed else 0}")
    print(json.dumps(stats), file=sys.stderr)
    sys.exit(0)
