"""Minimal generic ERC-20 on-chain read helpers over a public JSON-RPC endpoint. Generalizes
the exact pattern already proven in skills/self/spawn/scripts/usdc-balance.py (which hardcodes
one token/one chain) to any token/holder/chain, since this skill reads balances of two
different tokens (pUSD, USDC.e) on Polygon. No web3.py dependency for these two calls --
matches the existing precedent's own choice of raw urllib + eth_call.
"""
from __future__ import annotations

import json
import urllib.request
from typing import Optional


def erc20_balance_units(rpc_url: str, token_address: str, holder_address: str, timeout: int = 30) -> int:
    """Raw base-unit balanceOf(holder). Raises on RPC/network failure (fail-closed callers
    should treat an exception as "unknown, do not proceed" -- never silently treat as 0)."""
    holder_padded = holder_address.lower().replace("0x", "").rjust(64, "0")
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_call",
        "params": [{"to": token_address, "data": "0x70a08231" + holder_padded}, "latest"],
    }
    req = urllib.request.Request(
        rpc_url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "anicca-funding/1.0"},
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    if "result" not in resp:
        raise RuntimeError(f"eth_call error reading balanceOf({holder_address}) on {token_address}: {resp}")
    return int(resp["result"], 16)


def eth_tx_status(rpc_url: str, tx_hash: str, timeout: int = 30) -> Optional[str]:
    """Return the tx receipt's `status` field ('0x1' success / '0x0' revert), or None if the
    tx is not yet mined. This is the INDEPENDENT on-chain check money-safety rail §3 requires
    ("各送金は on-chain tx hash + status 0x1 を確認してから成功記録") -- callers must not treat an
    SDK/relayer "success" response alone as proof; they must see 0x1 here."""
    body = {"jsonrpc": "2.0", "id": 1, "method": "eth_getTransactionReceipt", "params": [tx_hash]}
    req = urllib.request.Request(
        rpc_url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "anicca-funding/1.0"},
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    result = resp.get("result")
    if not result:
        return None
    return result.get("status")


def eth_tx_confirmed_success(rpc_url: str, tx_hash: str, timeout: int = 30) -> bool:
    return eth_tx_status(rpc_url, tx_hash, timeout=timeout) == "0x1"
