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


def eth_get_transaction_receipt(rpc_url: str, tx_hash: str, timeout: int = 30) -> Optional[dict]:
    """Full tx receipt (status + logs) -- the fill-specific evidence
    `parse_erc20_transfer_amount` below needs. Returns None if the tx is not yet mined (RPC
    `result` is null); raises on RPC/network failure so callers fail closed on that (mirrors
    `eth_tx_status`'s contract -- an exception here must never be silently treated as "no
    fill")."""
    body = {"jsonrpc": "2.0", "id": 1, "method": "eth_getTransactionReceipt", "params": [tx_hash]}
    req = urllib.request.Request(
        rpc_url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "anicca-funding/1.0"},
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    return resp.get("result")


# keccak256("Transfer(address,address,uint256)") -- the fixed, universal ERC-20 Transfer event
# topic0. A constant of the on-chain machine format, not a judgment value.
ERC20_TRANSFER_TOPIC0 = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def parse_erc20_transfer_amount(*, logs, token_address: str, to_address: str) -> Optional[int]:
    """Pure parse (no I/O) of a transaction receipt's `logs` array -- a fixed on-chain machine
    format, not a judgment call (see rules/building-effective-ai-agents.md's judgment-regex vs
    fixed-format-parsing distinction) -- for an ERC-20 `Transfer(address,address,uint256)`
    event emitted BY `token_address` with `to` == `to_address`. This is the tx-SPECIFIC fill
    evidence (FIND-004): a wallet-wide balance delta alone cannot distinguish this fill from an
    unrelated concurrent inflow, but a Transfer log naming exactly this token and exactly this
    recipient can. Returns the raw base-unit amount (int) of the FIRST matching log, or None if
    no matching log exists at all -- callers must treat None as "delivery not proven", never as
    0 delivered."""
    token = (token_address or "").lower()
    to_padded = "0x" + (to_address or "").lower().replace("0x", "").rjust(64, "0")
    for log in logs or []:
        if not isinstance(log, dict):
            continue
        if (log.get("address") or "").lower() != token:
            continue
        topics = log.get("topics") or []
        if len(topics) < 3:
            continue
        if (topics[0] or "").lower() != ERC20_TRANSFER_TOPIC0:
            continue
        if (topics[2] or "").lower() != to_padded:
            continue
        data = log.get("data")
        if not data:
            continue
        try:
            return int(data, 16)
        except (TypeError, ValueError):
            continue
    return None
