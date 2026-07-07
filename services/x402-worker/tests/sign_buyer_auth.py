#!/usr/bin/env python3
"""Sign an EIP-3009 transferWithAuthorization as a MOCK BUYER and emit a base64
x-payment receipt for the x402-cloud Worker.

Two modes:
  --mode buyer   : fresh ephemeral buyer wallet signs (from == signer != pay_to) → Worker 200
  --mode selfsig : pay_to-style self-signed (from == to == signer) → Worker 402 (Wave-1 reject)

The EIP-712 domain/types mirror services/x402-worker/index.ts exactly so that
viem's recoverTypedDataAddress on the edge recovers the same address eth_account signs.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import secrets
import time

from eth_account import Account
from eth_account.messages import encode_typed_data

PAY_TO = "0xB9dd3B67921B354c656523d6851537988F31DD56"
BASE_CHAIN_ID = 8453
BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
PRICE_ATOMIC = 1000


def typed_data(frm: str, to: str, value: int, valid_after: int,
               valid_before: int, nonce: str) -> dict:
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
            "chainId": BASE_CHAIN_ID,
            "verifyingContract": BASE_USDC,
        },
        "message": {
            "from": frm,
            "to": to,
            "value": value,
            "validAfter": valid_after,
            "validBefore": valid_before,
            "nonce": nonce,
        },
    }


def build(mode: str) -> str:
    now = int(time.time())
    valid_after = 0
    valid_before = now + 3600
    nonce = "0x" + secrets.token_hex(32)

    if mode == "selfsig":
        # Wave-1 self-signed style: signer == pay_to, from == to == pay_to.
        # We cannot own pay_to's key here, so simulate the failure mode the Worker rejects:
        # an ephemeral key signs but claims from == to == PAY_TO. recovered != from → reject.
        acct = Account.create()
        frm = PAY_TO
        to = PAY_TO
    else:  # buyer
        acct = Account.create()
        frm = acct.address
        to = PAY_TO

    envelope = typed_data(frm, to, PRICE_ATOMIC, valid_after, valid_before, nonce)
    signable = encode_typed_data(full_message=envelope)
    signed = acct.sign_message(signable)

    receipt = {
        "protocol": "x402-exact-evm",
        "chain_id": BASE_CHAIN_ID,
        "verifying_contract": BASE_USDC,
        "from": frm,
        "to": to,
        "value_atomic": PRICE_ATOMIC,
        "valid_after": valid_after,
        "valid_before": valid_before,
        "nonce": nonce,
        "signature": signed.signature.hex() if signed.signature.hex().startswith("0x")
        else "0x" + signed.signature.hex(),
    }
    return base64.b64encode(json.dumps(receipt).encode("utf-8")).decode("ascii")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["buyer", "selfsig"], default="buyer")
    args = ap.parse_args()
    print(build(args.mode))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
