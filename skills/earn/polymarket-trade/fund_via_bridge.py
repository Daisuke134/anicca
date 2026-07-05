#!/usr/bin/env python3
"""fund_via_bridge.py — the CONFIRMED human-zero way to REGISTER + fund any instance's Polymarket
deposit wallet, so EVERY self-funded AI can trade on Polymarket from birth.

★ ROOT CAUSE this fixes (confirmed 2026-07-05, see SKILL.md "DEPOSIT-WALLET REGISTRY GATE"): the CLOB
rejects a deposit wallet with `error resolving address` / `wallet registry validation failed: not
registered` until the wallet is REGISTERED in Polymarket's relayer registry. Registration happens when
funds flow THROUGH Polymarket's Bridge / Collateral Onramp — NOT when you transfer pUSD directly to the
deposit wallet (that leaves it on-chain-deployed but UNregistered and stuck). ★

What this does (idempotent, no browser, no human credentials):
  1. Derive this instance's deposit wallet from POLYGON_WALLET_PRIVATE_KEY (SDK, POLY_1271 sig-3).
  2. If `get_balance_allowance` already resolves → ALREADY REGISTERED, just (re)approve spenders, exit 0.
  3. Else: POST https://bridge.polymarket.com/deposit {address: deposit_wallet} → EVM bridge address.
  4. Send >= $2 of a supported asset (USDC.e / native USDC / pUSD on Polygon) THROUGH the bridge address:
     - default source = THIS instance's own USDC.e/pUSD (env FUND_TOKEN, FUND_USD); the relayer
       transfer_erc20 must come from a REGISTERED wallet, so a fresh unfunded instance uses SOURCE_KEY
       (a registered colony wallet, e.g. automaton) for a one-time $2 mutual-aid registration deposit.
  5. Poll bridge /status until COMPLETED, then re-check `get_balance_allowance` → REGISTERED.
  6. Approve pUSD to the neg-risk exchange (0xe2222…) + adapter (0xd91E80…) — NOT 0x4bFb41d5 (blocked).

Env:
  POLYGON_WALLET_PRIVATE_KEY   THIS instance's EOA key (the deposit-wallet owner/signer).
  SOURCE_KEY (optional)        a REGISTERED wallet's key to send the one-time registration deposit
                               through the bridge (mutual aid). Defaults to POLYGON_WALLET_PRIVATE_KEY
                               when this instance is already funded+registered enough to self-fund.
  FUND_USD (default 2)         USD to route through the bridge for registration.

Prints one JSON line: {deposit_wallet, bridge_address, registered, balance_usdc}.
"""
import os, sys, json, base64, datetime, time
import requests
from eth_account import Account
from eth_account.messages import encode_defunct

PUSD = "0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB"
NEG_EXCH = "0xe2222d279d744050d28e00520010520000310F59"
NEG_ADAPTER = "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296"
BRIDGE = "https://bridge.polymarket.com"


def norm(k):
    return k if k.startswith("0x") else "0x" + k


def mint_relayer_key(acct):
    """SIWE (no browser) → relayer/api/auth → apiKey for gasless relayer transactions."""
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0", "Origin": "https://polymarket.com", "Referer": "https://polymarket.com/"})
    nonce = s.get("https://gamma-api.polymarket.com/nonce", timeout=20).json()["nonce"]
    iss = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + \
        f"{datetime.datetime.now(datetime.timezone.utc).microsecond//1000:03d}Z"
    f = {"domain": "polymarket.com", "address": acct.address, "statement": "Welcome to Polymarket! Sign to connect.",
         "uri": "https://polymarket.com", "version": "1", "chainId": 137, "nonce": nonce, "issuedAt": iss}
    pt = (f"polymarket.com wants you to sign in with your Ethereum account:\n{acct.address}\n\n{f['statement']}\n\n"
          f"URI: https://polymarket.com\nVersion: 1\nChain ID: 137\nNonce: {nonce}\nIssued At: {iss}")
    sig = "0x" + acct.sign_message(encode_defunct(text=pt)).signature.hex()
    b = base64.b64encode((json.dumps(f, separators=(",", ":")) + ":::" + sig).encode()).decode()
    s.get("https://gamma-api.polymarket.com/login", headers={"Authorization": "Bearer " + b}, timeout=20)
    r = s.post("https://relayer-v2.polymarket.com/relayer/api/auth", json={}, timeout=20).json()
    return r.get("apiKey") or r.get("api_key")


def client_for(key):
    from polymarket.clients.secure import SecureClient
    from polymarket.auth import RelayerApiKey
    acct = Account.from_key(key)
    return SecureClient.create(private_key=key, api_key=RelayerApiKey(key=mint_relayer_key(acct), address=acct.address)), acct


def is_registered(client):
    try:
        client.get_balance_allowance(asset_type="COLLATERAL")
        return True
    except Exception:
        return False


def approve_spenders(client):
    for sp in (NEG_EXCH, NEG_ADAPTER):
        try:
            h = client.approve_erc20(token_address=PUSD, spender_address=sp, amount="max")
            try:
                h.wait()
            except Exception:
                pass
        except Exception as e:
            print(f"[fund_via_bridge] approve {sp[:10]} note: {str(e)[:60]}", file=sys.stderr)


def main():
    key = norm(os.environ["POLYGON_WALLET_PRIVATE_KEY"])
    fund_usd = float(os.environ.get("FUND_USD", "2"))
    client, acct = client_for(key)
    deposit = str(client._ctx.wallet)
    print(f"[fund_via_bridge] EOA={acct.address} deposit={deposit}", file=sys.stderr)

    if is_registered(client):
        approve_spenders(client)
        print(json.dumps({"deposit_wallet": deposit, "registered": True, "already": True}))
        client.close()
        return

    # 1. bridge address for this deposit wallet
    addrs = requests.post(f"{BRIDGE}/deposit", json={"address": deposit}, timeout=20).json()["address"]
    bridge_evm = addrs["evm"]
    print(f"[fund_via_bridge] bridge EVM={bridge_evm}", file=sys.stderr)

    # 2. route funds THROUGH the bridge from a REGISTERED source (self if registered, else mutual-aid)
    source_key = norm(os.environ.get("SOURCE_KEY", key))
    src_client, src_acct = client_for(source_key)
    if not is_registered(src_client):
        print(json.dumps({"deposit_wallet": deposit, "registered": False,
                          "error": "source wallet not registered — pass SOURCE_KEY of a registered colony wallet"}))
        src_client.close(); client.close(); return
    amt = int(round(fund_usd * 1e6))
    h = src_client.transfer_erc20(token_address=PUSD, recipient_address=bridge_evm, amount=amt)
    try:
        h.wait()
    except Exception:
        pass
    src_client.close()
    print(f"[fund_via_bridge] sent ${fund_usd} pUSD through bridge, waiting for onramp…", file=sys.stderr)

    # 3. poll until the onramp registers the wallet (CLOB resolves)
    registered = False
    for _ in range(24):  # up to ~4 min
        time.sleep(10)
        if is_registered(client):
            registered = True
            break
    if registered:
        approve_spenders(client)
    bal = None
    try:
        ba = client.get_balance_allowance(asset_type="COLLATERAL")
        bal = float(getattr(ba, "balance", 0)) / 1e6
    except Exception:
        pass
    print(json.dumps({"deposit_wallet": deposit, "bridge_address": bridge_evm,
                      "registered": registered, "balance_usdc": bal}))
    client.close()


if __name__ == "__main__":
    main()
