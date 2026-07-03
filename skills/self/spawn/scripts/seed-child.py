#!/usr/bin/env python3
"""Seed a child wallet: real Base USDC transfer parent -> child. Prints the tx hash on success.
Usage: seed-child.py CHILD_ADDR AMOUNT_USDC PARENT_WALLET_JSON   [env: BASE_RPC_URL]
Fail-closed: any error (incl. receipt status != 1) => exit 1, nothing printed to stdout.
If the tx was broadcast but the receipt timed out, prints "PENDING <hash>" to stderr and
exits 2 so the caller can record the hash instead of double-spending (HARD 0.24 honest ledger)."""
import json
import os
import sys

from web3 import Web3
from eth_account import Account

USDC = Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
RPC = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
ERC20_ABI = json.loads('[{"constant":false,"inputs":[{"name":"to","type":"address"},{"name":"value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"type":"function"}]')

def main():
    child = Web3.to_checksum_address(sys.argv[1])
    amount_units = round(float(sys.argv[2]) * 10**6)
    w = json.load(open(sys.argv[3]))
    pk = w["private_key"]
    if not pk.startswith("0x"):
        pk = "0x" + pk
    acct = Account.from_key(pk)
    parent_addr = w.get("address", "")
    if parent_addr and acct.address.lower() != parent_addr.lower():
        print(f"seed-child: key derives {acct.address}, wallet.json says {parent_addr} — abort", file=sys.stderr)
        sys.exit(1)
    if child.lower() == acct.address.lower():
        print("seed-child: child == parent — abort", file=sys.stderr)
        sys.exit(1)

    w3 = Web3(Web3.HTTPProvider(RPC))
    usdc = w3.eth.contract(address=USDC, abi=ERC20_ABI)
    tx = usdc.functions.transfer(child, amount_units).build_transaction({
        "from": acct.address,
        "nonce": w3.eth.get_transaction_count(acct.address),
        "chainId": 8453,
        "maxFeePerGas": w3.eth.gas_price * 2,
        "maxPriorityFeePerGas": w3.to_wei(0.001, "gwei"),
    })
    h = w3.eth.send_raw_transaction(acct.sign_transaction(tx).raw_transaction)
    try:
        r = w3.eth.wait_for_transaction_receipt(h, timeout=180)
    except Exception:
        print(f"PENDING {h.hex()}", file=sys.stderr)
        sys.exit(2)
    if r.status != 1:
        print(f"seed-child: tx {h.hex()} reverted", file=sys.stderr)
        sys.exit(1)
    print(f"0x{h.hex().removeprefix('0x')}")

if __name__ == "__main__":
    main()
