#!/usr/bin/env python3
"""execute-ubi — on-chain sender for UBI. Reads a plan from env UBI_PLAN (built by lib/ubi.mjs),
sends ONE ERC20 USDC transfer per recipient FROM Anicca's own wallet, prints {txs:[{to,tx,status}]}.

No human, no Claude in the loop. Signs with the SAME wallet key the earn loop uses (BLOCKRUN_WALLET_KEY,
the execute-swap.py template). Sends ONLY Anicca's OWN USDC to recipient WALLETS — never any user data.

VERIFIED (ctx7 /websites/base + firecrawl basescan, 2026-06-16):
  USDC (Base mainnet) = 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913, decimals 6,
  transfer(address,uint256) selector = 0xa9059cbb.
"""
import json
import os
import sys

from web3 import Web3
from eth_account import Account

USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"   # ctx7 encodeProlink "USDC on Base"
TRANSFER_SELECTOR = "a9059cbb"                          # keccak4("transfer(address,uint256)")


def _wd(hexno: str) -> str:
    return hexno.lower().rjust(64, "0")


def _build_transfer(to: str, amount_base: int) -> str:
    return "0x" + TRANSFER_SELECTOR + _wd(to.replace("0x", "")) + _wd(format(int(amount_base), "x"))


def usdc_balance(w, addr, block="latest"):
    data = "0x70a08231" + _wd(addr.replace("0x", ""))
    res = w.eth.call({"to": Web3.to_checksum_address(USDC), "data": data}, block)
    return int(res.hex() or "0", 16)


def main():
    plan = json.loads(os.environ.get("UBI_PLAN", "{}"))
    transfers = plan.get("transfers", [])
    if not transfers:
        print(json.dumps({"txs": [], "error": "no_transfers"})); return
    pkvar = os.environ.get("PKVAR", "BLOCKRUN_WALLET_KEY")
    key = os.environ.get(pkvar) or os.environ.get("BLOCKRUN_WALLET_KEY")
    if not key:
        print(json.dumps({"txs": [], "error": f"no wallet key ({pkvar})"})); sys.exit(2)
    rpc = os.environ.get("BASE_RPC_URL", "https://mainnet.base.org")
    w = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 30}))
    acct = Account.from_key(key)
    me = acct.address

    # never overspend: total pool must not exceed our live USDC balance.
    total = sum(int(t["amount_base"]) for t in transfers)
    if usdc_balance(w, me) < total:
        print(json.dumps({"txs": [], "error": "insufficient_balance"})); return

    chain_id = w.eth.chain_id  # 8453 (Base) read live — no hardcode
    nonce = w.eth.get_transaction_count(me)
    gp = w.eth.gas_price
    out = []
    for t in transfers:
        to = Web3.to_checksum_address(t["to"])
        data = _build_transfer(to, int(t["amount_base"]))
        tx = {"to": Web3.to_checksum_address(USDC), "from": me, "value": 0, "data": data,
              "chainId": chain_id, "nonce": nonce}
        try:
            gas = w.eth.estimate_gas(tx)
        except Exception as e:
            out.append({"to": t["to"], "tx": "", "status": "0x0", "error": str(e)[:120]}); break
        tx["gas"] = int(gas * 12 // 10)
        tx["maxFeePerGas"] = gp * 2
        tx["maxPriorityFeePerGas"] = min(gp, w.to_wei(0.001, "gwei"))
        signed = acct.sign_transaction(tx)
        raw = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction")
        txh = w.eth.send_raw_transaction(raw)
        txhash = txh.hex()
        if not txhash.startswith("0x"):
            txhash = "0x" + txhash
        rcpt = w.eth.wait_for_transaction_receipt(txh, timeout=180)
        status = "0x1" if int(rcpt["status"]) == 1 else "0x0"
        out.append({"to": t["to"], "tx": txhash, "amount_base": t["amount_base"], "status": status})
        nonce += 1
        if status != "0x1":
            break  # stop on first failure; the bridge records the partial honestly
    print(json.dumps({"txs": out, "from": me.lower()}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({"txs": [], "error": str(e)[:300]}))
        sys.exit(1)
