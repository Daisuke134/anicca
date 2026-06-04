#!/usr/bin/env python3
"""Sign a demo x402 receipt with the Anicca wallet and emit it base64-encoded
on stdout. Drives the E2E test for x402_in_server.py.

In production, the BUYER signs and the SERVER verifies. In Wave 1 we use the
same wallet for both sides — proves the protocol plumbing without requiring
a second sovereign wallet (which #327 will mint per-child).
"""
from __future__ import annotations

import argparse
import base64
import json
import pathlib
import secrets
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import wallet_lib  # noqa: E402
from x402_in_server import receipt_typed_data  # noqa: E402

from eth_account.messages import encode_typed_data  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--route", default="/paid")
    ap.add_argument("--amount-atomic", type=int, default=1000)  # 0.001 USDC
    ap.add_argument("--valid-seconds", type=int, default=120)
    ap.add_argument(
        "--buyer-mode",
        choices=["self", "unsigned"],
        default="self",
        help=(
            "self (default): sign with the Anicca wallet (pay_to == signer — the valid "
            "Wave 1 prototype path). unsigned: forge a receipt that DECLARES pay_to "
            "== anicca but sign it with a fresh ephemeral key (hostile-buyer negative "
            "test — server MUST reject with 402)."
        ),
    )
    args = ap.parse_args()

    pay_to, anicca_signer = wallet_lib.load_signer()
    if args.buyer_mode == "self":
        signer = anicca_signer
    else:  # "unsigned" — fresh throwaway key, declares pay_to but does NOT own it
        from eth_account import Account as _Acct  # noqa: WPS433
        ephemeral = _Acct.create()
        signer = ephemeral
    nonce = "0x" + secrets.token_hex(32)
    expires_at = int(time.time()) + args.valid_seconds

    envelope = receipt_typed_data(
        route=args.route,
        pay_to=pay_to,
        amount_atomic=args.amount_atomic,
        nonce=nonce,
        expires_at=expires_at,
    )
    signable = encode_typed_data(full_message=envelope)
    signed = signer.sign_message(signable)
    sig_hex = signed.signature.hex()
    if not sig_hex.startswith("0x"):
        sig_hex = "0x" + sig_hex

    payload = {
        "route": args.route,
        "pay_to": pay_to,
        "amount_atomic": args.amount_atomic,
        "nonce": nonce,
        "expires_at": expires_at,
        "signature": sig_hex,
    }
    sys.stdout.write(base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
