#!/usr/bin/env python3
"""resolve.py — the MISSING resolver (fixes adversary FIND-001): marks decide.py's OPEN momentum paper
trades as `resolved` with a real `pnl_usdc`, so gate.py can ever produce PM_PAPER_PASS=1. For each open
`src=="momentum"` row whose 5-min window has closed, fetch the Binance 5-min candle covering that window,
decide up/down (close>open), compute win/loss via the PURE lib.side_won + lib.settle_pnl, and rewrite the
row in place. Effectful SHELL only; all P&L math is pure/tested in lib.py. Idempotent (only touches open).
"""
import json
import os
import sys
import time
import urllib.request
import pathlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/145 Safari/537.36"}
LEDGER = pathlib.Path(os.path.expanduser("~/loops/earn-pm-trade/paper-positions.jsonl"))


def get(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20))


def window_closed_up(window_start_ms):
    """True if the BTC 5-min candle starting at window_start_ms closed UP (close>open); None if unavailable."""
    try:
        k = get(f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=5m&startTime={int(window_start_ms)}&limit=1")
        if not k:
            return None
        o = float(k[0][1]); c = float(k[0][4])
        return c > o
    except Exception:
        return None


def resolve_all(ledger=LEDGER, now_ms=None, outcome_fn=None):
    """Resolve every open momentum row past its window_end. Returns (resolved_count, list_of_pnls).
    `outcome_fn(window_start_ms) -> bool|None` decides up/down; defaults to the live Binance reader so a test
    can inject a deterministic outcome (fixes untested-resolver, FIND-004)."""
    if now_ms is None:
        now_ms = int(time.time() * 1000)
    if outcome_fn is None:
        outcome_fn = window_closed_up
    if not ledger.exists():
        return (0, [])
    lines = ledger.read_text().splitlines()
    out_rows = []
    resolved = 0
    pnls = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            out_rows.append(line)
            continue
        if (r.get("src") == "momentum" and r.get("status") == "open"
                and r.get("window_end_ms") and now_ms >= r["window_end_ms"] and r.get("window_start_ms")):
            up = outcome_fn(r["window_start_ms"])
            if up is None:
                out_rows.append(json.dumps(r))  # leave open, retry next tick
                continue
            won = lib.side_won(r.get("side", ""), up)
            pnl = lib.settle_pnl(won, float(r.get("entry_price", 0)), float(r.get("size_usdc", 0)))
            r["status"] = "resolved"
            r["closed_up"] = bool(up)
            r["won"] = bool(won)
            r["pnl_usdc"] = round(pnl, 6)
            r["resolved_ts"] = int(time.time())
            resolved += 1
            pnls.append(pnl)
            out_rows.append(json.dumps(r))
        else:
            out_rows.append(json.dumps(r))
    if resolved:
        ledger.write_text("\n".join(out_rows) + "\n")
    return (resolved, pnls)


if __name__ == "__main__":
    n, pnls = resolve_all()
    print(json.dumps({"slot": "earn/pm-trade", "resolved": n, "net_usdc": round(sum(pnls), 6)}))
