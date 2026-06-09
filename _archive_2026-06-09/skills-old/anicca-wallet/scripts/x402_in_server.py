#!/usr/bin/env python3
"""x402 IN (earn) — minimal stdlib HTTP server.

Routes:
  GET /health  → 200 "ok"
  GET /paid    → 402 (no x-payment) or 200 (valid x-payment)

Off-chain verification only (Wave 1): the x-payment header is a base64 JSON
{route, pay_to, amount_atomic, nonce, expires_at, signature}. We require:
  * pay_to == anicca wallet
  * amount_atomic >= per-route price
  * expires_at > now
  * signature recovers to the same wallet that signed the demo (in production
    Wave 2 this is the BUYER's wallet, and we additionally verify a Base
    USDC transferWithAuthorization tx — out of Wave 1 scope; spec 09 T4-T5).

Wave 1 verifies WE can issue + verify our OWN receipt — it proves the
signature plumbing is sound end-to-end. This is a LOCAL RECEIPT PROTOTYPE,
NOT a production earn endpoint. A self-signed receipt where signer == pay_to
returns 200; an ephemeral-key-forged receipt where signer != pay_to returns
402 (test_x402_in_negative.sh proves this). Real buyer-signed flow + on-chain
settlement verification is Wave 2 follow-on #324-W2-in-buyer.
"""
from __future__ import annotations

import argparse
import base64
import json
import pathlib
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import wallet_lib  # noqa: E402

from eth_account import Account  # noqa: E402
from eth_account.messages import encode_typed_data  # noqa: E402

ROUTES = {
    "/paid": {"price_atomic": 1000, "label": "echo"},  # 0.001 USDC
}


def receipt_typed_data(route: str, pay_to: str, amount_atomic: int,
                       nonce: str, expires_at: int) -> dict:
    return {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
            ],
            "X402Receipt": [
                {"name": "route", "type": "string"},
                {"name": "pay_to", "type": "address"},
                {"name": "amount_atomic", "type": "uint256"},
                {"name": "nonce", "type": "bytes32"},
                {"name": "expires_at", "type": "uint256"},
            ],
        },
        "primaryType": "X402Receipt",
        "domain": {
            "name": "anicca-x402",
            "version": "1",
            "chainId": wallet_lib.BASE_CHAIN_ID,
        },
        "message": {
            "route": route,
            "pay_to": pay_to,
            "amount_atomic": amount_atomic,
            "nonce": nonce,
            "expires_at": expires_at,
        },
    }


def verify_receipt(header_b64: str, route: str, pay_to: str) -> Optional[str]:
    """Return recovered signer address if the receipt is valid; else None."""
    try:
        raw = base64.b64decode(header_b64).decode("utf-8")
        payload = json.loads(raw)
    except Exception:
        return None
    needed = ("route", "pay_to", "amount_atomic", "nonce", "expires_at", "signature")
    if not all(k in payload for k in needed):
        return None
    if payload["route"] != route:
        return None
    if payload["pay_to"].lower() != pay_to.lower():
        return None
    if int(payload["amount_atomic"]) < ROUTES[route]["price_atomic"]:
        return None
    if int(payload["expires_at"]) <= int(time.time()):
        return None
    envelope = receipt_typed_data(
        route=payload["route"],
        pay_to=payload["pay_to"],
        amount_atomic=int(payload["amount_atomic"]),
        nonce=payload["nonce"],
        expires_at=int(payload["expires_at"]),
    )
    signable = encode_typed_data(full_message=envelope)
    try:
        recovered = Account.recover_message(signable, signature=payload["signature"])
    except Exception:
        return None
    # Wave 1 prototype: the ONLY valid signer is pay_to itself (self-signed receipt loop).
    # An attacker who learns pay_to but does not own the key cannot forge a valid receipt.
    # Wave 2 replaces this with buyer-signed payment authorizations + on-chain settlement
    # verification (recovered == buyer wallet, plus Base USDC transferWithAuthorization tx).
    if recovered.lower() != payload["pay_to"].lower():
        return None
    return recovered


class X402Handler(BaseHTTPRequestHandler):
    pay_to: str = ""

    def log_message(self, fmt, *args):  # silence noisy access log in tests
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send_402(self, route: str) -> None:
        cfg = ROUTES[route]
        body = json.dumps({
            "error": "payment required",
            "route": route,
            "network": "base",
            "asset": wallet_lib.BASE_USDC,
            "amount_atomic": cfg["price_atomic"],
            "amount_usdc": cfg["price_atomic"] / 1_000_000,
            "pay_to": self.pay_to,
            "protocol": "x402-v1",
        }).encode("utf-8")
        self.send_response(402, "Payment Required")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header(
            "WWW-Authenticate",
            f'x402 network="base", asset="{wallet_lib.BASE_USDC}", '
            f'amount="{cfg["price_atomic"]}", pay_to="{self.pay_to}", route="{route}"',
        )
        self.send_header("x402-network", "base")
        self.send_header("x402-asset", wallet_lib.BASE_USDC)
        self.send_header("x402-amount", str(cfg["price_atomic"]))
        self.send_header("x402-pay-to", self.pay_to)
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if self.path == "/health":
            self._send_json(200, {"ok": True, "service": "anicca-x402-in", "wave": 1})
            return
        if self.path not in ROUTES:
            self._send_json(404, {"error": "no such route"})
            return
        header = self.headers.get("x-payment", "")
        if not header:
            self._send_402(self.path)
            return
        recovered = verify_receipt(header, self.path, self.pay_to)
        if not recovered:
            self._send_json(402, {"error": "invalid receipt"})
            return
        self._send_json(200, {
            "ok": True,
            "route": self.path,
            "recovered": recovered,
            "served_at": int(time.time()),
            "prototype": True,
            "note": (
                "Wave 1 local receipt prototype: receipt signed by pay_to wallet itself. "
                "Not a production earn endpoint. No facilitator, no EIP-3009 settlement, "
                "no on-chain transfer proof. Real buyer-signed flow + settlement = Wave 2."
            ),
        })


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8403)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    pay_to, _ = wallet_lib.load_signer()
    X402Handler.pay_to = pay_to
    httpd = HTTPServer((args.host, args.port), X402Handler)
    sys.stderr.write(f"x402-in listening on http://{args.host}:{args.port} pay_to={pay_to}\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
