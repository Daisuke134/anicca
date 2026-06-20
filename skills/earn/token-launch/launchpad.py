#!/usr/bin/env python3
"""launchpad.py — thin tool primitives for MoltX Token Launchpad on Base.

HARD RULE #0: this is the TOOL. It exposes only deterministic primitives. The
model — i.e. the anicca calling it — decides token name, symbol, logo, fee
recipients, airdrop strategy, when to launch, and whether to launch at all.
This file MUST NOT encode "what worked for me." See SKILL.md.

API: https://launchpad.moltx.io  (no API key, payment-based: 0.001 ETH ≈ $2.70)
Docs: https://launchpad.moltx.io/skill.md  (canonical)
Chain: Base (8453)

CLI usage (each subcommand returns JSON to stdout):
  launchpad.py deposit
  launchpad.py check-deposit <depositAddress>
  launchpad.py fund <depositAddress> <privateKey>
  launchpad.py deploy --deposit <addr> --name <s> --symbol <s> --image <url> \\
                       --owner <addr> --fee-recipient <addr>:<bps> [...]
  launchpad.py buy <tokenAddress> --deposit <addr>
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error

BASE_URL = os.environ.get("MOLTX_LAUNCHPAD_URL", "https://launchpad.moltx.io")
RPC_URL = os.environ.get("BASE_RPC_URL", "https://mainnet.base.org")
REQUIRED_ETH_WEI = 1_000_000_000_000_000  # 0.001 ETH


def _http_post(path, body):
    req = urllib.request.Request(
        BASE_URL + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read())
        except Exception:
            return {"ok": False, "error": str(e), "status": e.code}


def _http_get(path):
    req = urllib.request.Request(BASE_URL + path, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read())
        except Exception:
            return {"ok": False, "error": str(e), "status": e.code}


def cmd_deposit(_args):
    """POST /api/deposit — get a temporary deposit address that expires in 24h."""
    print(json.dumps(_http_post("/api/deposit", {}), indent=2))


def cmd_check_deposit(args):
    """GET /api/deposit/<addr> — check whether the deposit is funded."""
    print(json.dumps(_http_get(f"/api/deposit/{args.address}"), indent=2))


def cmd_fund(args):
    """Send exactly 0.001 ETH on Base from <privateKey> to <depositAddress>.

    Uses web3.py. The caller's wallet must hold ≥ 0.001 ETH + gas (~$0.01).
    This is a primitive — the model decides whether/when/from-which-wallet to fund.
    """
    from web3 import Web3
    from eth_account import Account

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    acct = Account.from_key(args.privateKey)
    deposit_to = Web3.to_checksum_address(args.address)
    nonce = w3.eth.get_transaction_count(acct.address, "pending")
    gas_price = max(int(w3.eth.gas_price * 2), int(0.05e9))
    tx = {
        "to": deposit_to,
        "value": REQUIRED_ETH_WEI,
        "gas": 21000,
        "gasPrice": gas_price,
        "nonce": nonce,
        "chainId": 8453,
    }
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    rcpt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    print(json.dumps({
        "ok": rcpt.status == 1,
        "txHash": "0x" + tx_hash.hex(),
        "block": rcpt.blockNumber,
        "from": acct.address,
        "to": deposit_to,
        "amountWei": REQUIRED_ETH_WEI,
    }, indent=2))


def _parse_fee_recipients(specs):
    """Parse --fee-recipient repeatable args of form 'address:bps[:admin]'."""
    out = []
    for spec in specs or []:
        parts = spec.split(":")
        if len(parts) < 2 or len(parts) > 3:
            raise SystemExit(f"--fee-recipient must be address:bps[:admin], got {spec!r}")
        entry = {"address": parts[0], "bps": int(parts[1])}
        if len(parts) == 3:
            entry["admin"] = parts[2]
        out.append(entry)
    return out


def cmd_deploy(args):
    """POST /api/deploy — atomic token + pool + LP + airdrop deploy."""
    fee_recipients = _parse_fee_recipients(args.fee_recipient)
    if sum(r["bps"] for r in fee_recipients) != 10000:
        raise SystemExit("fee_recipients bps must sum to 10000")
    body = {
        "depositAddress": args.deposit,
        "name": args.name,
        "symbol": args.symbol,
        "image": args.image,
        "tokenOwner": args.owner,
        "feeRecipients": fee_recipients,
    }
    if args.metadata:
        body["metadata"] = args.metadata
    if args.context:
        body["context"] = args.context
    if args.total_supply is not None:
        body["totalSupply"] = args.total_supply
    if args.lp_bps is not None:
        body["lpBps"] = args.lp_bps
    if args.airdrop_json:
        body["airdrop"] = json.loads(args.airdrop_json)
    if args.pool_config_json:
        body["poolConfig"] = json.loads(args.pool_config_json)
    print(json.dumps(_http_post("/api/deploy", body), indent=2))


def cmd_buy(args):
    """POST /api/deploy/<token>/buy — initial DEX-registering buy (strongly recommended)."""
    body = {"depositAddress": args.deposit}
    print(json.dumps(_http_post(f"/api/deploy/{args.token}/buy", body), indent=2))


def cmd_wait_funded(args):
    """Poll GET /api/deposit/<addr> until funded=true or timeout."""
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        r = _http_get(f"/api/deposit/{args.address}")
        if r.get("funded"):
            print(json.dumps({"ok": True, "funded": True, "balance": r.get("balance")}))
            return
        time.sleep(args.poll)
    print(json.dumps({"ok": False, "error": "timeout", "lastStatus": r}))
    sys.exit(1)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("deposit", help="create a new deposit address").set_defaults(fn=cmd_deposit)

    s = sub.add_parser("check-deposit", help="check whether a deposit is funded")
    s.add_argument("address")
    s.set_defaults(fn=cmd_check_deposit)

    s = sub.add_parser("wait-funded", help="poll until deposit is funded")
    s.add_argument("address")
    s.add_argument("--timeout", type=int, default=600)
    s.add_argument("--poll", type=int, default=5)
    s.set_defaults(fn=cmd_wait_funded)

    s = sub.add_parser("fund", help="send 0.001 ETH on Base to a deposit address")
    s.add_argument("address")
    s.add_argument("privateKey", help="sender private key (read from env when not given)")
    s.set_defaults(fn=cmd_fund)

    s = sub.add_parser("deploy", help="deploy ERC-20 + Fluid pool + LP (+ optional airdrop)")
    s.add_argument("--deposit", required=True, help="funded depositAddress")
    s.add_argument("--name", required=True)
    s.add_argument("--symbol", required=True)
    s.add_argument("--image", required=True, help="https:// or data:image/ URL")
    s.add_argument("--owner", required=True, help="ERC-20 owner address")
    s.add_argument("--fee-recipient", action="append", required=True,
                   help="repeat per recipient: address:bps[:admin]; bps must sum to 10000")
    s.add_argument("--metadata", default=None)
    s.add_argument("--context", default=None)
    s.add_argument("--total-supply", type=int, default=None, dest="total_supply")
    s.add_argument("--lp-bps", type=int, default=None, dest="lp_bps")
    s.add_argument("--airdrop-json", default=None, dest="airdrop_json",
                   help="JSON for airdrop field (see skill.md)")
    s.add_argument("--pool-config-json", default=None, dest="pool_config_json",
                   help="JSON for poolConfig field (see skill.md)")
    s.set_defaults(fn=cmd_deploy)

    s = sub.add_parser("buy", help="initial DEX-registering buy on a just-deployed token")
    s.add_argument("token")
    s.add_argument("--deposit", required=True)
    s.set_defaults(fn=cmd_buy)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
