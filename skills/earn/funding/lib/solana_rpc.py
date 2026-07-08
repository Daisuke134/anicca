"""Minimal Solana JSON-RPC read helpers (balance + signature status) via raw urllib, matching
the same request-construction style already used in skills/earn/sol-to-usdc.py (that file's
`rpc()` helper), generalized into a reusable module instead of a copy-pasted inline closure.
"""
from __future__ import annotations

import json
import urllib.request
from typing import Optional


def _rpc(rpc_url: str, method: str, params: list, timeout: int = 30) -> dict:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(rpc_url, data=body, headers={"Content-Type": "application/json"})
    resp = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    if "error" in resp:
        raise RuntimeError(f"solana rpc {method} error: {resp['error']}")
    return resp["result"]


def spl_token_balance_units(rpc_url: str, owner_address: str, mint: str, timeout: int = 30) -> int:
    """Sum of raw base-unit balances across all token accounts `owner_address` holds for
    `mint`. Returns 0 if the owner holds no account for this mint (not an error)."""
    result = _rpc(
        rpc_url,
        "getTokenAccountsByOwner",
        [owner_address, {"mint": mint}, {"encoding": "jsonParsed"}],
        timeout=timeout,
    )
    total = 0
    for entry in result.get("value", []):
        info = entry["account"]["data"]["parsed"]["info"]
        total += int(info["tokenAmount"]["amount"])
    return total


def get_signature_status(rpc_url: str, signature: str, timeout: int = 30) -> Optional[dict]:
    result = _rpc(
        rpc_url,
        "getSignatureStatuses",
        [[signature], {"searchTransactionHistory": True}],
        timeout=timeout,
    )
    values = result.get("value", [None])
    return values[0] if values else None


def confirmed_success(rpc_url: str, signature: str, timeout: int = 30) -> bool:
    """The INDEPENDENT on-chain check for the Solana leg (mirrors erc20.eth_tx_confirmed_success
    for the EVM legs) -- a CLI/SDK exit code alone is not proof; this queries chain state
    directly and requires both no error AND a confirmed/finalized commitment."""
    status = get_signature_status(rpc_url, signature, timeout=timeout)
    if not status:
        return False
    if status.get("err") is not None:
        return False
    return status.get("confirmationStatus") in ("confirmed", "finalized")
