#!/usr/bin/env python3
"""execute-swap — the on-chain executor for the earn skill's EARN_STRATEGY=swap path.

No human, no Claude in the loop: run.sh sets EARN_MODE=execute and calls this. It quotes
ETH->USDC on Uniswap V3 (Base), signs with the wallet key, broadcasts, waits for the receipt,
and prints a JSON result {tx, status, before_usdc, after_usdc, gross_usdc, cost_usdc} for run.sh
to record. The calldata layout MUST match skills/earn/lib/swap.mjs (selector 0x04e45aaf,
7 ABI words) — that contract is unit-tested in lib/__tests__/swap.test.js.

Env:
  BLOCKRUN_WALLET_KEY (or PKVAR-named)  wallet private key (signs + receives USDC)
  BASE_RPC_URL          default https://mainnet.base.org
  EARN_SWAP_ETH         default 0.0003  (ETH amount in)
  EARN_SLIPPAGE_BPS     default 100     (1.0%)
  EARN_MIN_ETH_RESERVE  default 0.0005  (keep this much ETH for gas; below -> abort, no brick)
"""
import json
import os
import sys
import time

from web3 import Web3
from eth_account import Account

WETH = "0x4200000000000000000000000000000000000006"
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
ROUTER = "0x2626664c2603336E57B271c5C0b26F421741e481"  # Uniswap SwapRouter02 (Base)
QUOTER = "0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a"  # QuoterV2 (Base)
EXACT_INPUT_SINGLE_SELECTOR = "04e45aaf"
USDC_SEL_BALANCEOF = "70a08231"


def _wd(hexno: str) -> str:
    return hexno.lower().rjust(64, "0")


def _uw(v: int) -> str:
    if int(v) < 0:
        raise ValueError("negative uint")
    return _wd(format(int(v), "x"))


def _aw(a: str) -> str:
    return _wd(a.replace("0x", ""))


def build_exact_input_single_data(token_in, token_out, fee, recipient, amount_in, amount_out_min):
    # Mirror of swap.mjs buildExactInputSingleData (param order verbatim).
    return (
        "0x"
        + EXACT_INPUT_SINGLE_SELECTOR
        + _aw(token_in)
        + _aw(token_out)
        + _uw(fee)
        + _aw(recipient)
        + _uw(amount_in)
        + _uw(amount_out_min)
        + _uw(0)  # sqrtPriceLimitX96
    )


def min_out(quoted, bps):
    bps = int(bps)
    if bps < 0 or bps > 10000:
        raise ValueError("slippageBps 0..10000")
    return (int(quoted) * (10000 - bps)) // 10000


def usdc_balance(w, addr):
    data = "0x" + USDC_SEL_BALANCEOF + _aw(addr)
    res = w.eth.call({"to": Web3.to_checksum_address(USDC), "data": data})
    return int(res.hex() or "0", 16)


def quote_out(w, amount_in, fee):
    abi = [{
        "inputs": [{"components": [
            {"name": "tokenIn", "type": "address"},
            {"name": "tokenOut", "type": "address"},
            {"name": "amountIn", "type": "uint256"},
            {"name": "fee", "type": "uint24"},
            {"name": "sqrtPriceLimitX96", "type": "uint160"}],
            "name": "params", "type": "tuple"}],
        "name": "quoteExactInputSingle",
        "outputs": [
            {"name": "amountOut", "type": "uint256"},
            {"name": "sqrtPriceX96After", "type": "uint160"},
            {"name": "initializedTicksCrossed", "type": "uint32"},
            {"name": "gasEstimate", "type": "uint256"}],
        "stateMutability": "nonpayable", "type": "function"}]
    q = w.eth.contract(address=Web3.to_checksum_address(QUOTER), abi=abi)
    out = q.functions.quoteExactInputSingle(
        (Web3.to_checksum_address(WETH), Web3.to_checksum_address(USDC), int(amount_in), int(fee), 0)
    ).call()
    return int(out[0])


def main():
    pkvar = os.environ.get("PKVAR", "BLOCKRUN_WALLET_KEY")
    key = os.environ.get(pkvar) or os.environ.get("BLOCKRUN_WALLET_KEY")
    if not key:
        print(json.dumps({"error": f"no wallet key in env ({pkvar})"}))
        sys.exit(2)
    rpc = os.environ.get("BASE_RPC_URL", "https://mainnet.base.org")
    eth_in = float(os.environ.get("EARN_SWAP_ETH", "0.0003"))
    slippage_bps = int(os.environ.get("EARN_SLIPPAGE_BPS", "100"))
    min_reserve = float(os.environ.get("EARN_MIN_ETH_RESERVE", "0.0005"))
    fee = int(os.environ.get("EARN_SWAP_FEE", "500"))

    w = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 30}))
    acct = Account.from_key(key)
    me = acct.address
    amount_in = w.to_wei(eth_in, "ether")

    eth_bal = w.eth.get_balance(me)
    # Survival guard: never spend below the gas reserve (no-brick).
    if eth_bal < w.to_wei(eth_in + min_reserve, "ether"):
        print(json.dumps({"abort": "eth_below_reserve",
                          "eth_balance": eth_bal / 1e18,
                          "need": eth_in + min_reserve}))
        sys.exit(3)

    before = usdc_balance(w, me)
    quoted = quote_out(w, amount_in, fee)
    amount_out_min = min_out(quoted, slippage_bps)
    data = build_exact_input_single_data(WETH, USDC, fee, me, amount_in, amount_out_min)

    tx = {
        "to": Web3.to_checksum_address(ROUTER),
        "from": me,
        "value": int(amount_in),
        "data": data,
        "chainId": w.eth.chain_id,
        "nonce": w.eth.get_transaction_count(me),
    }
    gas = w.eth.estimate_gas(tx)
    tx["gas"] = int(gas * 12 // 10)
    gp = w.eth.gas_price
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
    after = usdc_balance(w, me)
    gross = (after - before) / 1e6
    gas_used = int(rcpt["gasUsed"])
    eff_price = int(rcpt.get("effectiveGasPrice", gp))
    cost_eth = gas_used * eff_price / 1e18
    # cost in USDC terms: value the gas ETH at the swap's realized ETH/USDC rate.
    eth_usdc_rate = (gross / eth_in) if eth_in > 0 and gross > 0 else 0
    cost_usdc = round(cost_eth * eth_usdc_rate, 6)

    print(json.dumps({
        "tx": txhash,
        "status": status,
        "before_usdc": before / 1e6,
        "after_usdc": after / 1e6,
        "gross_usdc": round(gross, 6),
        "cost_usdc": cost_usdc,
        "gas_used": gas_used,
        "amount_in_eth": eth_in,
        "wallet": me.lower(),
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({"error": str(e)[:300]}))
        sys.exit(1)
