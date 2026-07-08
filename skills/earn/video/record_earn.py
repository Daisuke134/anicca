"""record_earn.py — INV-7: count ONLY real EXTERNAL on-chain USDC inflows as earnings. NEVER count
"posted"/"submitted"/"applied" as earned (that's why past skills reported success but earned ¥0). Idempotent:
the same tx_hash is never double-counted. Pure + file-only (testable).

A valid earning entry MUST be a verified USDC inflow:
  token == "USDC", amount > 0, direction == "in", a non-empty tx_hash, verified is True.
Anything else → ("rejected", reason). Already-seen tx_hash → ("duplicate", tx). Else append → ("recorded", amount).

★ TRUST BOUNDARY (FIND-503) ★ — this is a PURE SCHEMA GATE, not an on-chain oracle. The `verified` flag is
trusted, so the producer that writes the inflow source (~/.cloak/earn-video-inflows.jsonl) is RESPONSIBLE for
the actual on-chain confirmation (tx exists on Base, token==USDC, recipient==our wallet, amount matches) BEFORE
setting verified:true. That on-chain detector is NOT built yet → today there is NO producer → the ledger stays
empty (honest: we record nothing rather than fabricate). `verify_onchain` below is the hook the detector should
call; until a real chain check is wired, it returns False so a self-declared verified:true alone CANNOT be paid.
"""
import json, os

def is_real_usdc_inflow(e):
    return (
        isinstance(e, dict)
        and e.get("token") == "USDC"
        and isinstance(e.get("amount"), (int, float)) and not isinstance(e.get("amount"), bool) and e.get("amount", 0) > 0
        and e.get("direction") == "in"
        and bool(e.get("tx_hash"))
        and e.get("verified") is True
    )

def verify_onchain(entry):
    """Real on-chain confirmation hook (FIND-503 / REQ-LV-080, P0-4). Wired to onchain.py's
    confirm_usdc_inflow — a real Base RPC log-filter check (correct USDC contract + Transfer topic0
    + `to`-topic + matching amount, fail-closed on any RPC error/mismatch). Inject a stub in tests
    to simulate a confirmed tx without hitting the network."""
    try:
        from onchain import confirm_usdc_inflow  # same directory (skills/earn/video/)
        return confirm_usdc_inflow(entry)
    except Exception:
        return False  # fail-closed: any import/RPC error never fabricates a confirmed inflow


def _key(e):
    # dedup on (tx_hash, log_index) so a tx carrying TWO legit USDC transfers isn't under-counted (log_index
    # absent ⇒ None, so single-transfer entries dedup on tx_hash exactly as before)
    return (e.get("tx_hash"), e.get("log_index"))

def _seen_tx(ledger_path):
    seen = set()
    if os.path.exists(ledger_path):
        for line in open(ledger_path):
            line = line.strip()
            if not line:
                continue
            try:
                seen.add(_key(json.loads(line)))
            except Exception:
                pass
    return seen

def record_earn(entry, ledger_path, onchain_check=None):
    check = onchain_check or verify_onchain
    if not is_real_usdc_inflow(entry):
        return ("rejected", "not a verified external USDC inflow")
    if not check(entry):
        return ("rejected", "tx_hash not confirmed on-chain (fail-closed: verified flag alone is not trusted)")
    if _key(entry) in _seen_tx(ledger_path):
        return ("duplicate", entry["tx_hash"])
    os.makedirs(os.path.dirname(ledger_path) or ".", exist_ok=True)
    with open(ledger_path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return ("recorded", entry["amount"])
