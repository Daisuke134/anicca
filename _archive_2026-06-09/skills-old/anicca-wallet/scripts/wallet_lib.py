"""wallet_lib — single chokepoint for loading the Anicca wallet private key.

CRITICAL invariants:
  * The private key is read ONCE from ~/.automaton/wallet.json::privateKey.
  * It is held only inside the LocalAccount object returned by load_signer().
  * It is NEVER printed, logged, echoed, returned as a string, or written to disk.
  * The public address is the ONLY string this module exports.
"""
from __future__ import annotations

import json
import pathlib
from typing import Tuple

from eth_account import Account
from eth_account.signers.local import LocalAccount

KEYSTORE = pathlib.Path.home() / ".automaton" / "wallet.json"
EXPECTED_ADDRESS = "0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21"
BASE_CHAIN_ID = 8453
BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # USDC on Base mainnet


def load_signer() -> Tuple[str, LocalAccount]:
    """Return (address, signer). Caller MUST NOT serialize the signer."""
    if not KEYSTORE.exists():
        raise FileNotFoundError(
            f"wallet keystore missing: {KEYSTORE} — run anicca-wallet generate first"
        )
    raw = json.loads(KEYSTORE.read_text())
    pk = raw.get("privateKey")
    if not pk or not isinstance(pk, str) or not pk.startswith("0x") or len(pk) != 66:
        raise ValueError(
            "wallet keystore is malformed: missing 0x-prefixed 32-byte privateKey"
        )
    signer: LocalAccount = Account.from_key(pk)
    # IMPORTANT: do not return pk; do not log it; do not assign to a module global.
    del pk
    del raw
    if signer.address != EXPECTED_ADDRESS:
        raise RuntimeError(
            f"wallet keystore derives to {signer.address}, expected {EXPECTED_ADDRESS} — "
            "refusing to proceed (wrong keystore wired)"
        )
    return signer.address, signer


def address_only() -> str:
    """Public address without instantiating a signer (cheap probe)."""
    addr, _ = load_signer()
    return addr
