#!/usr/bin/env python3
"""
place_order.py — EXECUTION: generalized V2 FAK order placement (#25 spec §2.2).

The EXACT working path as v2_full_flow.py (SecureClient sig-3 credential
bootstrap + relayer-key mint via SIWE + get_order_book + create_market_order
FAK + post_order), generalized so TOKEN_ID/SIDE/AMOUNT are INPUTS, never
hardcoded. WHICH market/side/amount is entirely pick.py's (the model's)
decision — this file only executes it and enforces the money-safety cap.

Inputs (env preferred, positional argv fallback):
  TOKEN_ID   CLOB token id to BUY                              (argv[1])
  SIDE       must be "BUY" — this flow only supports BUY;
             SELL needs shares already held, out of scope here (argv[2])
  AMOUNT     USD spend amount                                  (argv[3])
  POLYGON_WALLET_PRIVATE_KEY  this instance's signer key (read via the
                              agent's own .env, same as fund_via_bridge.py)
  MAX_BET_SIZE (default 2)   hard cap on AMOUNT (money-safety, not judgment)
  PM_TRADE_AGENT_HOME        override for the base agent home (default below)

Output: exactly one line of JSON on stdout:
  {"token_id","amount","order_id","post_result","ok"}
On any failure before an order can be attempted: {"ok": false, "error": "..."}
(exit code 1). Never places a fake/simulated order — no dry-run path exists.
"""
import os
import sys
import json
import base64
import datetime
import requests
from eth_account import Account
from eth_account.messages import encode_defunct
from dotenv import load_dotenv

AGENT_HOME = os.environ.get(
    "PM_TRADE_AGENT_HOME",
    os.path.expanduser("~/.anicca-founder/agents/polymarket-agent"),
)
load_dotenv(os.path.join(AGENT_HOME, ".env"))

PUSD = "0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB"
NEG_EXCH = "0xe2222d279d744050d28e00520010520000310F59"
NEG_ADAPTER = "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296"
DEFAULT_MAX_BET_SIZE = 2.0
SLIPPAGE = 0.03


def _arg(i):
    return sys.argv[i] if len(sys.argv) > i else None


def fail(reason):
    print(json.dumps({"ok": False, "error": reason}))
    sys.exit(1)


def mint_relayer_key(acct):
    """SIWE (no browser) -> gamma-api/login -> relayer-v2/relayer/api/auth
    -> apiKey. Identical to v2_full_flow.py / fund_via_bridge.py."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://polymarket.com",
        "Referer": "https://polymarket.com/",
    })
    nonce = s.get("https://gamma-api.polymarket.com/nonce", timeout=20).json()["nonce"]
    now = datetime.datetime.now(datetime.timezone.utc)
    iss = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"
    fields = {
        "domain": "polymarket.com",
        "address": acct.address,
        "statement": "Welcome to Polymarket! Sign to connect.",
        "uri": "https://polymarket.com",
        "version": "1",
        "chainId": 137,
        "nonce": nonce,
        "issuedAt": iss,
    }
    plaintext = (
        f"polymarket.com wants you to sign in with your Ethereum account:\n{acct.address}\n\n"
        f"{fields['statement']}\n\nURI: https://polymarket.com\nVersion: 1\nChain ID: 137\n"
        f"Nonce: {nonce}\nIssued At: {iss}"
    )
    sig = "0x" + acct.sign_message(encode_defunct(text=plaintext)).signature.hex()
    b64 = base64.b64encode((json.dumps(fields, separators=(",", ":")) + ":::" + sig).encode()).decode()
    s.get("https://gamma-api.polymarket.com/login", headers={"Authorization": "Bearer " + b64}, timeout=20)
    resp = s.post("https://relayer-v2.polymarket.com/relayer/api/auth", json={}, timeout=20).json()
    return resp.get("apiKey") or resp.get("api_key")


def approve_spenders(client):
    """Idempotent — fund_via_bridge.py already does this at registration
    time; re-approving here is safe and covers a freshly-registered wallet
    whose approvals haven't landed yet."""
    for spender in (NEG_EXCH, NEG_ADAPTER):
        balance_allowance = client.get_balance_allowance(asset_type="COLLATERAL")
        if int(balance_allowance.allowances.get(spender, 0)) < 1:
            handle = client.approve_erc20(token_address=PUSD, spender_address=spender, amount="max")
            try:
                handle.wait()
            except Exception:
                pass


def best_ask_price(order_book):
    asks = getattr(order_book, "asks", [])
    if not asks:
        return 0.58  # last-resort fallback, matches v2_full_flow.py's proven value
    return min(float(getattr(a, "price", None) or a["price"]) for a in asks)


def main():
    token_id = os.environ.get("TOKEN_ID") or _arg(1)
    side = (os.environ.get("SIDE") or _arg(2) or "BUY").upper()
    amount_raw = os.environ.get("AMOUNT") or _arg(3)

    if not token_id:
        fail("missing TOKEN_ID")
    if side != "BUY":
        fail(f"unsupported SIDE:{side} (this flow only executes BUY)")
    if not amount_raw:
        fail("missing AMOUNT")

    try:
        amount = float(amount_raw)
    except (TypeError, ValueError):
        fail(f"invalid AMOUNT:{amount_raw}")

    max_bet_size = float(os.environ.get("MAX_BET_SIZE", DEFAULT_MAX_BET_SIZE))
    if amount > max_bet_size:
        amount = max_bet_size  # money-safety cap (spec §2.2) — not a judgment call

    key = os.environ.get("POLYGON_WALLET_PRIVATE_KEY")
    if not key:
        fail("missing POLYGON_WALLET_PRIVATE_KEY")
    key = key if key.startswith("0x") else "0x" + key

    from polymarket.clients.secure import SecureClient
    from polymarket.auth import RelayerApiKey

    acct = Account.from_key(key)
    bootstrap = SecureClient._create(private_key=key, validate_credentials=True)
    credentials = bootstrap._ctx.credentials
    bootstrap.close()

    client = SecureClient.create(
        private_key=key,
        credentials=credentials,
        api_key=RelayerApiKey(key=mint_relayer_key(acct), address=acct.address),
    )

    try:
        approve_spenders(client)

        order_book = client.get_order_book(token_id=token_id)
        ask = best_ask_price(order_book)
        max_price = str(round(ask + SLIPPAGE, 3))

        signed_order = client.create_market_order(
            token_id=token_id,
            side="BUY",
            amount=str(amount),
            max_price=max_price,
            order_type="FAK",
        )
        response = client.post_order(signed_order)

        try:
            post_result = response.model_dump(mode="json")
        except Exception:
            post_result = str(response)

        print(json.dumps({
            "token_id": token_id,
            "amount": amount,
            "order_id": getattr(response, "order_id", None),
            "post_result": post_result,
            "ok": bool(getattr(response, "ok", False)),
        }))
    finally:
        client.close()


if __name__ == "__main__":
    main()
