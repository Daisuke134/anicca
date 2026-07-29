#!/usr/bin/env python3
"""
ensure-polymarket-deposit-wallet.py — born-with-Polygon (#27 EQUALIZE).

Given ANY instance's own EVM private key (POLYGON_WALLET_PRIVATE_KEY env var, no
dotenv, no hardcoded path — so this is safe to run for automaton / Franklin / any
future spawn, each with its OWN key), deploy that EOA's Polymarket CLOB V2 deposit
wallet (signature_type=3 / POLY_1271, ERC-1167 proxy) via the SIWE -> relayer flow.

This is GASLESS (Polymarket's relayer pays; the EOA only SIGNS) and IDEMPOTENT
(calling it again just re-authenticates; it does not redeploy an existing wallet).
No funds are moved or required — this only grants the ADDRESS the instance can
later fund (with pUSD / bridged USDC) to actually trade. See
__REPO_ROOT__/skills/earn/polymarket-trade/SKILL.md for the funding + trading recipe.

Prints ONE line of JSON to stdout: {"eoa", "deposit_wallet", "deployed"}.
All diagnostics go to stderr. Never prints the private key.
"""
import os
import sys
import json
import base64
import datetime

import requests
from eth_account import Account
from eth_account.messages import encode_defunct

GAMMA = "https://gamma-api.polymarket.com"
RELAYER = "https://relayer-v2.polymarket.com"
CHAIN = 137


def log(*args):
    print(*args, file=sys.stderr)


def main():
    raw_key = os.environ.get("POLYGON_WALLET_PRIVATE_KEY")
    if not raw_key:
        log("[pm-deposit-wallet] no POLYGON_WALLET_PRIVATE_KEY in env — skipping")
        return 0
    key = raw_key if raw_key.startswith("0x") else "0x" + raw_key
    acct = Account.from_key(key)
    addr = acct.address
    log("[pm-deposit-wallet] EOA:", addr)

    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://polymarket.com",
        "Referer": "https://polymarket.com/",
    })

    r = s.get(f"{GAMMA}/nonce", timeout=20)
    log("[pm-deposit-wallet] nonce HTTP", r.status_code)
    if r.status_code != 200:
        log("[pm-deposit-wallet] nonce fetch failed — skipping (offline?)")
        return 0
    nonce = r.json().get("nonce")

    issued = (
        datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.")
        + f"{datetime.datetime.now(datetime.timezone.utc).microsecond // 1000:03d}Z"
    )
    fields = {
        "domain": "polymarket.com",
        "address": addr,
        "statement": "Welcome to Polymarket! Sign to connect.",
        "uri": "https://polymarket.com",
        "version": "1",
        "chainId": CHAIN,
        "nonce": nonce,
        "issuedAt": issued,
    }
    plaintext = (
        f"{fields['domain']} wants you to sign in with your Ethereum account:\n"
        f"{addr}\n\n{fields['statement']}\n\n"
        f"URI: {fields['uri']}\nVersion: {fields['version']}\n"
        f"Chain ID: {CHAIN}\nNonce: {nonce}\nIssued At: {issued}"
    )
    sig_hex = "0x" + acct.sign_message(encode_defunct(text=plaintext)).signature.hex()
    combined = json.dumps(fields, separators=(",", ":")) + ":::" + sig_hex
    bearer = base64.b64encode(combined.encode()).decode()

    r = s.get(f"{GAMMA}/login", headers={"Authorization": "Bearer " + bearer}, timeout=20)
    log("[pm-deposit-wallet] login HTTP", r.status_code)

    r = s.post(f"{RELAYER}/relayer/api/auth", json={}, timeout=20)
    log("[pm-deposit-wallet] relayer/auth HTTP", r.status_code)
    if r.status_code != 200:
        log("[pm-deposit-wallet] relayer auth failed:", r.text[:200], "— skipping (non-blocking)")
        return 0
    api_key = r.json().get("apiKey") or r.json().get("api_key")

    try:
        from polymarket.clients.secure import SecureClient
        from polymarket.auth import RelayerApiKey
        from web3 import Web3
    except ImportError as e:
        log("[pm-deposit-wallet] missing python deps:", e, "— skipping (non-blocking)")
        return 0

    tmp = SecureClient._create(private_key=key, validate_credentials=True)
    creds = tmp._ctx.credentials
    deposit_wallet = str(tmp._ctx.wallet)
    tmp.close()
    log("[pm-deposit-wallet] deposit wallet address:", deposit_wallet)

    client = SecureClient.create(
        private_key=key,
        credentials=creds,
        api_key=RelayerApiKey(key=api_key, address=addr),
    )
    log("[pm-deposit-wallet] client ready (deploy is gasless via relayer, idempotent).")

    w3 = Web3(Web3.HTTPProvider(os.environ.get("POLYGON_RPC_URL", "https://polygon-bor-rpc.publicnode.com")))
    code = w3.eth.get_code(w3.to_checksum_address(deposit_wallet))
    deployed = len(code) > 2
    log("[pm-deposit-wallet] deployed on-chain:", deployed)
    client.close()

    print(json.dumps({"eoa": addr, "deposit_wallet": deposit_wallet, "deployed": deployed}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
