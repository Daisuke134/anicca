"""PROP-RL-LIVE1 independent verification script.
Run from ~/anicca main checkout, ANICCA_HOME unset.
(1) calls the real lib.ledger_reader.resolve_ledger_path()/realized_summary() against the real ledger
(2) independently hand-parses the same JSONL file with plain json.loads, applying REQ-RL5/RL6's
    is_profitable definition by hand (not calling ledger_reader's own function), and compares.
"""
import json
import os
import sys

SELF_IMPROVE_DIR = "/Users/operator/anicca/skills/earn/self-improve"
sys.path.insert(0, SELF_IMPROVE_DIR)

from lib import ledger_reader  # noqa: E402

assert "ANICCA_HOME" not in os.environ, "this script must run with ANICCA_HOME unset"

# --- (1) resolve_ledger_path + realized_summary, calling the REAL functions ---
path, resolved, source = ledger_reader.resolve_ledger_path()
summary = ledger_reader.realized_summary()

expected_path = "/Users/operator/anicca/skills/earn/state/earn-ledger.jsonl"
print(f"resolve_ledger_path() -> path={path!r} resolved={resolved!r} source={source!r}")
print(f"expected_path={expected_path!r}")
assert path == expected_path, f"PATH MISMATCH: {path} != {expected_path}"
assert resolved is True
assert source == "file_relative_default"
print("PASS: resolve_ledger_path() resolves to the exact real claude-p ledger file")

print()
print(f"realized_summary() = {json.dumps(summary, indent=2)}")

# --- (2) hand-computed independent parse, NOT calling ledger_reader.is_profitable at all ---
SWAP_SOURCES = {"swap-eth-usdc", "swap", "swap-usdc-eth"}

def hand_is_profitable(row: dict) -> bool:
    try:
        net = float(row.get("net_usdc", 0))
    except (TypeError, ValueError):
        return False
    if not (net > 0):
        return False
    if str(row.get("source")) in SWAP_SOURCES:
        return False
    if row.get("external") is not True:
        return False
    evm_ok = bool(row.get("tx")) and row.get("status") == "0x1"
    sol_ok = bool(row.get("sig")) and row.get("confirmed") is True
    hl_ok = (
        row.get("chain") == "hyperliquid"
        and row.get("fill_tid") is not None
        and row.get("confirmed") is True
    )
    return bool(evm_ok or sol_ok or hl_ok)

hand_rows = []
total_lines = 0
with open(expected_path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        total_lines += 1
        obj = json.loads(line)
        hand_rows.append(obj)

hand_profitable = [r for r in hand_rows if hand_is_profitable(r)]
hand_net = round(sum(float(r.get("net_usdc", 0)) for r in hand_profitable), 6)

print()
print(f"hand-parsed total_rows={total_lines}")
print(f"hand-parsed profitable_row_count={len(hand_profitable)}")
print(f"hand-parsed realized_net_usd={hand_net}")
print("hand-parsed profitable rows (task, net_usdc):")
for r in hand_profitable:
    print(f"  {r.get('task')!r} net_usdc={r.get('net_usdc')}")

print()
assert summary["total_rows"] == total_lines, (summary["total_rows"], total_lines)
assert summary["profitable_row_count"] == len(hand_profitable), (summary["profitable_row_count"], len(hand_profitable))
assert summary["realized_net_usd"] == hand_net, (summary["realized_net_usd"], hand_net)
print(f"PASS: realized_summary()['realized_net_usd']={summary['realized_net_usd']} == hand-computed {hand_net}")
print()
print("=== PROP-RL-LIVE1: ALL ASSERTIONS PASSED ===")
