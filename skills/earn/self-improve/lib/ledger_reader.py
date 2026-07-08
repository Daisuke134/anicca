"""ledger_reader.py — close-loop Gap 1 fix: the self-improve harness's OBSERVE step, reading the
REAL realized P&L ledger before every evolve run.

Read-only Python mirror of `skills/_shared/lib/ledger.mjs`'s `readLedger`/`isProfitable` semantics.
This module NEVER writes to `earn-ledger.jsonl` or any other ledger file — it only ever reads
(`open(path, "r")`), matching REQ-EV7/INV-6's "fitness computation and ledger mutation are
structurally different code paths" pattern already established for the backtest evaluator.

Why a PORT instead of calling the real `ledger.mjs` (INV-5 tension, disclosed): behavioral-spec.md's
INV-5 says "no second parallel ledger reader/writer is introduced" and names
`skills/_shared/lib/ledger.mjs` as the one shared interface. That invariant was written before this
close-loop revision needed a Python-side OBSERVE step inside a fully-Python evaluation harness
(`evaluator.py`/`run_evolve.sh` intentionally have NO subprocess/node dependency — `subprocess` is
even on `scope_guard.py`'s own DENYLIST_MODULES for the EVOLVE-BLOCK, and shelling out to `node`
from this harness's own tooling would be the first subprocess dependency it has ever had). Rather
than add a subprocess->node round trip for a single read+filter, this module re-implements
`isProfitable`'s exact boolean logic in pure Python, read-only, over the SAME ledger file path and
the SAME field semantics — this is the pragmatic, honest trade-off: a duplicated (not divergent)
read-only VIEW of one field, not a second ledger, and never a writer. If `ledger.mjs`'s
`isProfitable` semantics ever change, this file must be updated to match (checked by
`tests/test_ledger_reader.py`'s fixtures, which mirror `skills/_shared/lib/ledger.mjs`'s own
module-docstring examples: a real EVM row, a real Solana row, a narrate-only row, and a swap row).

`isProfitable` mirrored EXACTLY (skills/_shared/lib/ledger.mjs, read directly): a profitable wake
needs (1) `net_usdc > 0`, (2) NOT a swap source (`swap-eth-usdc`/`swap`/`swap-usdc-eth` — asset
rotation is never earning), (3) `external is True` (proven external inbound revenue), AND (4) a
chain-correct confirmation: EVM (`tx` present AND `status == "0x1"`) OR Solana (`sig` present AND
`confirmed is True`).
"""
from __future__ import annotations

import json
import os
from typing import Optional

DEFAULT_LEDGER_PATH = os.path.join(
    os.path.expanduser("~"), "anicca", "skills", "earn", "state", "earn-ledger.jsonl"
)

# Mirrors skills/_shared/lib/ledger.mjs::SWAP_SOURCES verbatim.
SWAP_SOURCES = frozenset({"swap-eth-usdc", "swap", "swap-usdc-eth"})


def read_ledger(path: str = DEFAULT_LEDGER_PATH) -> list:
    """Read every JSONL line into a dict. Missing file -> [] (never raises). Blank or malformed
    (non-JSON, or JSON that isn't an object) lines are skipped — mirrors
    `ledger.mjs::readLedger`'s own `.filter(Boolean)` / try-catch-null behavior exactly."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        return []
    rows = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def is_profitable(line: Optional[dict]) -> bool:
    """Mirrors `ledger.mjs::isProfitable` exactly (see module docstring for the 4-part rule)."""
    if not line:
        return False
    try:
        net_usdc = float(line.get("net_usdc", 0))
    except (TypeError, ValueError):
        return False
    if not (net_usdc > 0):
        return False
    if str(line.get("source")) in SWAP_SOURCES:
        return False
    if line.get("external") is not True:
        return False
    evm_ok = bool(line.get("tx")) and line.get("status") == "0x1"
    sol_ok = bool(line.get("sig")) and line.get("confirmed") is True
    # REQ-C4 (feature hl-realized-pnl, documented follow-up, NOT implemented here): ledger.mjs's
    # isProfitable gained a third disjunct for a well-formed Hyperliquid fill (chain=="hyperliquid"
    # AND fill_tid present AND confirmed is True). Porting that check to this Python mirror is
    # deferred to a separate feature; this function does not yet recognize Hyperliquid lines.
    return evm_ok or sol_ok


def realized_summary(
    path: str = DEFAULT_LEDGER_PATH,
    window_start_ts: Optional[float] = None,
    window_end_ts: Optional[float] = None,
) -> dict:
    """The OBSERVE-step summary `run_evolve.sh` logs before every evolve run: real, ledger-derived
    realized net USD + the count of isProfitable rows, optionally restricted to
    `[window_start_ts, window_end_ts)` (unix seconds, `ledger.mjs`'s own `ts` convention — omit
    both for the ledger's full all-time history). A sparse or entirely-missing ledger degrades
    gracefully to an all-zero summary — this function never raises for a missing/empty/malformed
    ledger file (REQ-EV6-style fail-sentinel convention, applied here to a read, not a backtest)."""
    rows = read_ledger(path)
    total_rows = len(rows)
    profitable_rows = []
    for row in rows:
        ts = row.get("ts")
        if window_start_ts is not None and (ts is None or ts < window_start_ts):
            continue
        if window_end_ts is not None and (ts is None or ts >= window_end_ts):
            continue
        if is_profitable(row):
            profitable_rows.append(row)
    realized_net_usd = sum(float(r.get("net_usdc", 0)) for r in profitable_rows)
    return {
        "ledger_path": path,
        "total_rows": total_rows,
        "profitable_row_count": len(profitable_rows),
        "realized_net_usd": round(realized_net_usd, 6),
    }


if __name__ == "__main__":
    # Runnable as `python3 lib/ledger_reader.py` for run_evolve.sh's OBSERVE step: prints ONE line
    # of JSON to stdout (nothing else), so a caller can log/parse it directly.
    print(json.dumps(realized_summary()))
