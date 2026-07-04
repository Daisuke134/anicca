#!/usr/bin/env python3
"""
Polymarket CLOB V2 trading recipe — the STEEL primitives every Anicca can reuse.

WHY THIS FILE EXISTS
--------------------
Polymarket migrated its exchange to **CLOB V2 on 2026-04-28**. Every V1 SDK
(`py-clob-client<=0.34.6`, `@polymarket/clob-client<=5.8.1`) is permanently
rejected with `400 invalid order version, please use the latest clob-client`.
V2 also introduced a native stablecoin **pUSD** as the only collateral, and it
only accepts orders from a **registered deposit wallet** (signature_type=3,
POLY_1271, an ERC-1167 minimal proxy owned by your EOA).

This module encodes the WHOLE recipe so a "dumb" AI can earn without
re-deriving it. Every constant below was verified on-chain 2026-07-04.

Sources (all quoted, no guessing):
  - Polymarket/py-clob-client-v2 issue #92 (migration checklist comment)
  - crp4222/pmq/docs/war-story.md  (every V2 error verbatim + fix)
  - the installed py_clob_client_v2 (1.0.2) config.py  (ground-truth contracts)

STATUS (honest, no scam): funding (Relay->pUSD) and order build+post are
PROVEN live. Real matched fill requires a registered deposit wallet
(see `ensure_deposit_wallet`), which is the last integration step.
"""
from __future__ import annotations
import os, time, json
from decimal import Decimal
from dataclasses import dataclass

# ---- Verified V2 constants on Polygon (chain 137), from py_clob_client_v2/config.py ----
CHAIN_ID = 137
PUSD = "0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB"           # V2 collateral (symbol pUSD)
EXCHANGE_V2 = "0xE111180000d2663C0091e4f400237545B87B996B"    # CTF Exchange V2
NEG_RISK_EXCHANGE_V2 = "0xe2222d279d744050d28e00520010520000310F59"
CONDITIONAL_TOKENS = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
HOST = "https://clob.polymarket.com"
POLYGON_RPC = os.getenv("POLYGON_RPC", "https://polygon-bor-rpc.publicnode.com")

# Common origin USDC addresses for Relay funding (any chain -> Polygon pUSD)
USDC = {
    8453: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",   # Base USDC (native)
    137:  "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",   # Polygon USDC (native)
    137137: "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174", # Polygon USDC.e (bridged)
}

# Fee schedule (official docs 2026-07-03). Makers pay 0. Takers: rate*p*(1-p)*shares.
FEE_RATE = {"crypto": 0.07, "sports": 0.03, "finance": 0.04, "politics": 0.04,
            "economics": 0.05, "culture": 0.05, "weather": 0.05, "geopolitics": 0.0}


def _erc20(w3, addr):
    return w3.eth.contract(address=w3.to_checksum_address(addr), abi=[
        {"constant": True, "inputs": [{"name": "a", "type": "address"}], "name": "balanceOf",
         "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
        {"constant": False, "inputs": [{"name": "to", "type": "address"}, {"name": "v", "type": "uint256"}],
         "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    ])


def pusd_balance(address: str) -> float:
    """pUSD balance (float, 6 decimals) of any address on Polygon."""
    from web3 import Web3
    w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))
    return _erc20(w3, PUSD).functions.balanceOf(w3.to_checksum_address(address)).call() / 1e6


# --------------------------------------------------------------------------
# STEP 1 — FUND: swap USDC on ANY chain -> Polygon pUSD via Relay (PROVEN live)
# --------------------------------------------------------------------------
def fund_with_relay(signer_key: str, origin_chain: int, origin_usdc: str,
                    usd: float, recipient: str) -> dict:
    """
    Cross-chain swap origin USDC -> Polygon pUSD, delivered to `recipient`.
    Verified 2026-07-04: Base USDC $5 -> 4.95 pUSD on Polygon, real txs.
    Returns {'tx': [...], 'pusd_out': float}.
    """
    import requests
    from web3 import Web3
    from eth_account import Account
    key = signer_key if signer_key.startswith("0x") else "0x" + signer_key
    acct = Account.from_key(key)
    amount = str(int(round(usd * 1e6)))
    q = requests.post("https://api.relay.link/quote", json={
        "user": acct.address, "recipient": recipient,
        "originChainId": origin_chain, "destinationChainId": CHAIN_ID,
        "originCurrency": origin_usdc, "destinationCurrency": PUSD,
        "amount": amount, "tradeType": "EXACT_INPUT",
    }, timeout=30).json()
    if "steps" not in q:
        raise RuntimeError(f"relay quote error: {json.dumps(q)[:300]}")
    rpc = {8453: "https://base-rpc.publicnode.com", 137: POLYGON_RPC}[origin_chain]
    w3 = Web3(Web3.HTTPProvider(rpc))
    txs = []
    for step in q["steps"]:
        for item in step.get("items", []):
            if item.get("status") == "complete" or not item.get("data"):
                continue
            d = item["data"]
            tx = {"from": acct.address, "to": w3.to_checksum_address(d["to"]),
                  "data": d["data"], "value": int(d.get("value", "0")),
                  "chainId": d["chainId"], "nonce": w3.eth.get_transaction_count(acct.address, "pending"),
                  "gas": int(d.get("gas", 300000)),
                  "maxFeePerGas": int(d.get("maxFeePerGas", w3.eth.gas_price * 2)),
                  "maxPriorityFeePerGas": int(d.get("maxPriorityFeePerGas", 1_000_000))}
            h = w3.eth.send_raw_transaction(acct.sign_transaction(tx).raw_transaction)
            r = w3.eth.wait_for_transaction_receipt(h, timeout=180)
            if r.status != 1:
                raise RuntimeError(f"relay tx failed: {h.hex()}")
            txs.append(h.hex())
            chk = item.get("check")
            if chk:
                url = chk["endpoint"]
                url = ("https://api.relay.link" + url) if url.startswith("/") else url
                for _ in range(60):
                    time.sleep(5)
                    s = requests.get(url, timeout=15).json().get("status")
                    if s in ("success", "complete", "done"):
                        break
                    if s in ("failure", "refund"):
                        raise RuntimeError(f"relay bridge failed: {s}")
    det = q.get("details", {})
    return {"tx": txs, "pusd_out": float(det.get("currencyOut", {}).get("amountFormatted", 0))}


# --------------------------------------------------------------------------
# STEP 2 — DEPOSIT WALLET: V2 only accepts orders from a registered deposit
#   wallet (signature_type=3 / POLY_1271, ERC-1167 proxy owned by your EOA).
#   war-story §3: eth_call owner() (0x8da5cb5b); returns EOA + ~45-byte
#   ERC-1167 bytecode => it is YOUR deposit wallet -> use signature_type=3.
# --------------------------------------------------------------------------
def is_deposit_wallet(candidate: str, eoa: str) -> bool:
    """True if `candidate` is a deployed ERC-1167 deposit wallet owned by `eoa`."""
    from web3 import Web3
    w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))
    code = w3.eth.get_code(w3.to_checksum_address(candidate))
    if not code or len(code) < 40 or len(code) > 60:   # ERC-1167 minimal proxy ~45 bytes
        return False
    try:
        owner = w3.eth.call({"to": w3.to_checksum_address(candidate), "data": "0x8da5cb5b"})
        return owner[-20:].hex().lower() == eoa[2:].lower()
    except Exception:
        return False


def ensure_deposit_wallet(eoa: str) -> str | None:
    """
    Return the caller's registered Polymarket deposit wallet, or None if it
    must still be created. Creation = one-time onboarding at polymarket.com
    (the app deploys + registers the ERC-1167 POLY_1271 proxy for your EOA).
    A raw EOA (sig 0) and a Gnosis-Safe proxy (sig 2) are BOTH rejected with
    `maker address not allowed, please use the deposit wallet flow`.
    Once created, deposit pUSD to it and trade with signature_type=3.
    """
    dw = os.getenv("POLYMARKET_DEPOSIT_WALLET")
    if dw and is_deposit_wallet(dw, eoa):
        return dw
    return None


# --------------------------------------------------------------------------
# STEP 3 — TRADE: market-buy path (war-story §1: FAK/FOK buys ARE market
#   orders; the limit path fails with `invalid amounts ... max 2 decimals`).
# --------------------------------------------------------------------------
def make_client(signer_key: str, deposit_wallet: str):
    from py_clob_client_v2.client import ClobClient
    key = signer_key if signer_key.startswith("0x") else "0x" + signer_key
    c = ClobClient(HOST, chain_id=CHAIN_ID, key=key, signature_type=3, funder=deposit_wallet)
    creds = c.create_or_derive_api_key()
    c.set_api_creds(creds)
    return c


def market_buy(client, token_id: str, usd: float, price_cap: float, neg_risk: bool):
    """
    Real market BUY. `usd` = dollars to spend (rounded DOWN to cent),
    `price_cap` = max price you accept. Returns the raw CLOB response
    (may carry an orderID even on a clean no-fill — war-story §2).
    """
    from py_clob_client_v2.clob_types import MarketOrderArgsV2, PartialCreateOrderOptions, OrderType
    usd = int(usd * 100) / 100.0
    args = MarketOrderArgsV2(token_id=token_id, amount=usd, side="BUY", price=price_cap)
    opts = PartialCreateOrderOptions(neg_risk=neg_risk)
    return client.create_and_post_market_order(args, opts, order_type=OrderType.FAK)


def taker_fee(rate: float, price: float, shares: float) -> float:
    """war-story §5: fee = rate * p * (1-p) * shares. Makers pay 0."""
    return rate * price * (1 - price) * shares


if __name__ == "__main__":
    # self-check: print the verified constants + current pUSD on the founder wallet
    eoa = os.getenv("EOA", "0x810F6D61F7606dEEE2657d3083E150a222Bc29C5")
    print("V2 exchange:", EXCHANGE_V2, "| collateral pUSD:", PUSD)
    print("deposit wallet:", ensure_deposit_wallet(eoa) or "NOT REGISTERED (onboard at polymarket.com)")
