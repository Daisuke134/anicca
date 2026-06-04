#!/usr/bin/env python3
"""x402 OUT (pay) — produce a SIGNED EIP-3009 `transferWithAuthorization` USDC payload.

Dry-run by design: prints JSON to stdout with the signature and the address recovered
from the signature. Does NOT submit to the chain. The wallet's private key is loaded
via wallet_lib (chokepoint) and is NEVER printed / logged.

Spec refs:
  * EIP-3009 (USDC transferWithAuthorization): https://eips.ethereum.org/EIPS/eip-3009
  * x402 v0.5 protocol uses this exact primitive (Coinbase, Base — see 09-EARN-X402-LIVE.md § 0).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import secrets
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import wallet_lib  # noqa: E402

from eth_account import Account  # noqa: E402
from eth_account.messages import encode_typed_data  # noqa: E402


def build_transfer_authorization(
    from_addr: str,
    to_addr: str,
    value_atomic: int,
    valid_after: int,
    valid_before: int,
    nonce_hex: str,
) -> dict:
    """Construct the EIP-712 typed-data envelope USDC expects."""
    return {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "TransferWithAuthorization": [
                {"name": "from", "type": "address"},
                {"name": "to", "type": "address"},
                {"name": "value", "type": "uint256"},
                {"name": "validAfter", "type": "uint256"},
                {"name": "validBefore", "type": "uint256"},
                {"name": "nonce", "type": "bytes32"},
            ],
        },
        "primaryType": "TransferWithAuthorization",
        "domain": {
            "name": "USD Coin",
            "version": "2",
            "chainId": wallet_lib.BASE_CHAIN_ID,
            "verifyingContract": wallet_lib.BASE_USDC,
        },
        "message": {
            "from": from_addr,
            "to": to_addr,
            "value": value_atomic,
            "validAfter": valid_after,
            "validBefore": valid_before,
            "nonce": nonce_hex,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", required=True, help="recipient 0x address (checksummed ok)")
    ap.add_argument("--amount-usdc", type=float, required=True,
                    help="amount in USDC (e.g. 0.01 = 1 cent)")
    ap.add_argument("--valid-seconds", type=int, default=600,
                    help="how long the authorization stays valid (default 600s)")
    args = ap.parse_args()

    if not args.to.startswith("0x") or len(args.to) != 42:
        print(json.dumps({"error": "invalid --to (must be 0x + 40 hex chars)"}))
        return 2
    if args.amount_usdc <= 0:
        print(json.dumps({"error": "amount must be > 0"}))
        return 2

    value_atomic = int(round(args.amount_usdc * 1_000_000))  # USDC = 6 decimals
    now = int(time.time())
    valid_after = now - 60
    valid_before = now + args.valid_seconds
    # 32-byte random nonce, 0x + 64 hex chars
    nonce_hex = "0x" + secrets.token_hex(32)

    from_addr, signer = wallet_lib.load_signer()
    envelope = build_transfer_authorization(
        from_addr, args.to, value_atomic, valid_after, valid_before, nonce_hex,
    )
    # encode_typed_data builds the EIP-712 digest correctly for v4 typed data.
    signable = encode_typed_data(full_message=envelope)
    signed = signer.sign_message(signable)
    sig_hex = signed.signature.hex()
    if not sig_hex.startswith("0x"):
        sig_hex = "0x" + sig_hex

    # Recover — proves the signature is valid and to which address it resolves.
    recovered = Account.recover_message(signable, signature=sig_hex)

    payload = {
        "protocol": "x402-eip3009",
        "chain_id": wallet_lib.BASE_CHAIN_ID,
        "verifying_contract": wallet_lib.BASE_USDC,
        "from": from_addr,
        "to": args.to,
        "value_atomic": value_atomic,
        "value_usdc": args.amount_usdc,
        "valid_after": valid_after,
        "valid_before": valid_before,
        "nonce": nonce_hex,
        "signature": sig_hex,
        "recovered_signer": recovered,
        "broadcast": False,
        "note": "dry-run: signed off-chain only; broadcasting handled by Wave 2.",
    }
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
