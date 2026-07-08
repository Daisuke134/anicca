"""Append-only funding-ledger.jsonl -- the auditable, on-chain-evidenced record of every
funding decision + transfer. Mirrors the shape of skills/self/spawn/lib/ledger.js
(read/append JSONL), reimplemented in Python since this skill's scripts are Python (the PM
leg requires the installed `polymarket` SDK, Python-only).

Rail this encodes: docs/loop-engineering/11-parent-funding-loop.md §3
"MUST 全 decision + tx を funding-ledger.jsonl に記録".
"""
from __future__ import annotations

import json
import os
import time
from typing import Optional


def read_ledger(path: str) -> list[dict]:
    """Returns [] when the ledger doesn't exist yet (first run) -- never raises for that."""
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def append_ledger(path: str, row: dict) -> dict:
    """Append one JSON line. Creates parent dirs if needed. Returns the row unchanged
    (so callers can chain: `row = append_ledger(path, build_row(...))`)."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    return row


def build_row(
    *,
    step: str,
    amount_usd: float,
    status: str,
    reason: str = "",
    tx_hash: Optional[str] = None,
    from_addr: Optional[str] = None,
    to_addr: Optional[str] = None,
    ts: Optional[float] = None,
    extra: Optional[dict] = None,
) -> dict:
    """Pure row builder -- no I/O, no mutation of `extra`. `step` in
    {"withdraw","bridge","send_to_franklin"}. `status` in
    {"sent","pending","failed","skipped","dry"}. Only `status == "sent"` rows represent a REAL
    on-chain-confirmed transfer. `"pending"` means a tx/signature was broadcast (money may
    already be moving) but its confirmation could not yet be recorded -- written immediately
    after broadcast, before waiting for the terminal outcome, so a crash in the
    confirmation-RPC call never leaves a real transfer completely unlogged (money-safety
    adversary review Finding A, 2026-07-08). See lib/caps.py's `_outflow_rows` for how
    'pending' rows are counted toward caps without double-counting once a terminal 'sent'/
    'failed' row for the same tx_hash is later appended."""
    row = {
        "ts": ts if ts is not None else time.time(),
        "step": step,
        "amount_usd": amount_usd,
        "status": status,
        "reason": reason,
        "tx_hash": tx_hash,
        "from": from_addr,
        "to": to_addr,
    }
    if extra:
        row = {**row, **extra}
    return row
