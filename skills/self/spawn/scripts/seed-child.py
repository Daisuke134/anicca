#!/usr/bin/env python3
"""Transfer Base USDC parent -> child (REAL broadcast, waits for receipt). spawn-auto-seed REQ-4.
Usage: seed-child.py <child_address> <amount_units_6dec>
Env:   PARENT_WALLET_JSON (path with .address/.private_key), BASE_RPC_URL (optional)
Prints "SEED_TX=0x..." on success (receipt status 1); any failure => nonzero exit, no fake output.
Deterministic tool — moves exactly what it is told, decides nothing.
"""
import json, os, sys

from web3 import Web3

USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # Base USDC
ERC20_ABI = json.loads('[{"constant":false,"inputs":[{"name":"to","type":"address"},{"name":"value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"type":"function"}]')


def main():
    child = Web3.to_checksum_address(sys.argv[1])
    amount_units = int(sys.argv[2])
    assert amount_units > 0, "amount must be > 0"

    wallet_path = os.environ["PARENT_WALLET_JSON"]
    w = json.load(open(wallet_path))
    pk = w["private_key"]
    if not pk.startswith("0x"):
        pk = "0x" + pk

    w3 = Web3(Web3.HTTPProvider(os.getenv("BASE_RPC_URL", "https://mainnet.base.org")))
    assert w3.is_connected(), "Base RPC unreachable"
    from eth_account import Account
    acct = Account.from_key(pk)
    assert acct.address.lower() != child.lower(), "child == parent"

    usdc = w3.eth.contract(address=Web3.to_checksum_address(USDC), abi=ERC20_ABI)
    tx = usdc.functions.transfer(child, amount_units).build_transaction({
        "from": acct.address,
        "nonce": w3.eth.get_transaction_count(acct.address),
        "chainId": 8453,
        "maxFeePerGas": w3.eth.gas_price * 2,
        "maxPriorityFeePerGas": w3.to_wei(0.001, "gwei"),
    })
    h = w3.eth.send_raw_transaction(acct.sign_transaction(tx).raw_transaction)
    r = w3.eth.wait_for_transaction_receipt(h, timeout=180)
    if r.status != 1:
        print(f"seed-child: tx reverted {h.hex()}", file=sys.stderr)
        sys.exit(1)
    print(f"SEED_TX=0x{h.hex().removeprefix('0x')}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print(f"seed-child: {e}", file=sys.stderr)
        sys.exit(1)
