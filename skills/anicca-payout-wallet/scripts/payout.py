#!/usr/bin/env python3
"""anicca-payout-wallet — Tier 3 payout: USDC direct to user wallet on Base.

Reads broker state for the destination address. Computes amount as
PAYOUT_PERCENT of wallet_usd unless --amount is passed. Calls the cdp CLI
to send the transfer. Logs tx hash in state/sent.json and mails a receipt.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".openclaw" / "skills" / "_shared"))
import anicca_profile as prof  # noqa: E402

JST = timezone(timedelta(hours=9))
HOME = Path.home() / ".openclaw"
ENV = (HOME / ".env").read_text()
BROKER_STATE = HOME / "skills" / "anicca-fuel-broker" / "state" / "broker.json"
SENT_LOG = Path(__file__).resolve().parent.parent / "state" / "sent.json"
CFO_FILE = HOME / "skills" / "cfo-core" / "data" / "anicca-cfo.json"
PAYOUT_PERCENT = float(os.environ.get("PAYOUT_PERCENT", "10"))
BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # Base mainnet USDC


def env(name, default=""):
    m = re.search(rf"^{name}=(.*)$", ENV, re.M)
    return (m.group(1).strip().strip('"').strip("'") if m else default)


def read_broker_state():
    try:
        return json.loads(BROKER_STATE.read_text())
    except Exception:
        return {}


def read_cfo_wallet():
    try:
        d = json.loads(CFO_FILE.read_text())
        w = d.get("wallet") or {}
        return float(w.get("base_usdc") or w.get("usd_total") or 0)
    except Exception:
        return 0.0


def load_sent():
    try:
        return json.loads(SENT_LOG.read_text())
    except Exception:
        return []


def save_sent(entries):
    SENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    SENT_LOG.write_text(json.dumps(entries, ensure_ascii=False, indent=2))


def send_via_cdp(to_addr, amount_usd):
    """Invoke `cdp wallet send`. Returns tx hash or None.

    The cdp CLI from Coinbase AgentKit must be installed and configured
    with CDP_API_KEY_NAME + CDP_API_KEY_PRIVATE env vars.
    """
    if not (env("CDP_API_KEY_NAME") and env("CDP_API_KEY_PRIVATE")):
        print("[payout] cdp CLI not configured — install coinbase agentkit first",
              file=sys.stderr)
        return None
    # Amount in atomic USDC units (6 decimals)
    atomic = round(amount_usd * 1_000_000)
    try:
        out = subprocess.run(
            ["cdp", "wallet", "send",
             "--to", to_addr,
             "--token", BASE_USDC,
             "--network", "base-mainnet",
             "--amount", str(atomic)],
            capture_output=True, text=True, timeout=90,
            env={**os.environ,
                 "CDP_API_KEY_NAME": env("CDP_API_KEY_NAME"),
                 "CDP_API_KEY_PRIVATE": env("CDP_API_KEY_PRIVATE")},
        )
    except FileNotFoundError:
        print("[payout] cdp binary not in PATH", file=sys.stderr)
        return None
    if out.returncode != 0:
        print(f"[payout] cdp send failed: {out.stderr[:300]}", file=sys.stderr)
        return None
    # Parse tx hash from stdout (varies by cdp version)
    m = re.search(r"(0x[a-fA-F0-9]{64})", out.stdout)
    return m.group(1) if m else (out.stdout.strip() or None)


def send_receipt_mail(to_addr, amount_usd, tx_hash):
    acct = env("GOG_ACCOUNT") or prof.google_account()
    to = env("ANICCA_REPORT_TO") or acct
    if not (acct and to):
        return False
    body = (
        f"Hi,\n\n"
        f"I sent you ${amount_usd:.2f} USDC to your wallet on Base mainnet.\n\n"
        f"To:   {to_addr}\n"
        f"Tx:   {tx_hash or '(pending — see basescan)'}\n"
        f"Link: https://basescan.org/tx/{tx_hash or ''}\n\n"
        f"Settlement is on-chain, so you can verify yourself. There's no\n"
        f"intermediary holding this — once basescan confirms, it's yours.\n\n"
        f"— Anicca (payout-wallet, Tier 3)\n"
    )
    subj = f"[Anicca] Sent you ${amount_usd:.2f} USDC — Tier 3 payout"
    out = subprocess.run(
        ["/opt/homebrew/bin/gog", "gmail", "send",
         "--account", acct, "--to", to, "--subject", subj, "--body-file", "-"],
        input=body, capture_output=True, text=True,
        env={**os.environ,
             "GOG_ACCOUNT": acct,
             "GOG_KEYRING_PASSWORD": env("GOG_KEYRING_PASSWORD")},
        timeout=45,
    )
    return out.returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", help="override destination 0x address")
    ap.add_argument("--amount", type=float, help="override amount in USD")
    ap.add_argument("--dry-run", action="store_true",
                    help="print what would be sent, do not call cdp")
    args = ap.parse_args()

    broker = read_broker_state()
    to_addr = args.to or broker.get("payout_destination") or env("WALLET_ADDR")
    if not (to_addr and to_addr.startswith("0x")):
        print(json.dumps({"action": "no-destination",
                          "hint": "set broker.payout_destination or WALLET_ADDR"},
                         ensure_ascii=False))
        return

    wallet_usd = read_cfo_wallet()
    if args.amount is not None:
        amount = args.amount
    else:
        amount = round(wallet_usd * PAYOUT_PERCENT / 100, 2)

    if amount <= 0:
        print(json.dumps({"action": "no-funds", "wallet_usd": wallet_usd}))
        return

    if args.dry_run:
        print(json.dumps({"action": "dry-run", "to": to_addr,
                          "amount_usd": amount, "wallet_usd": wallet_usd},
                         ensure_ascii=False))
        return

    tx = send_via_cdp(to_addr, amount)
    entries = load_sent()
    entries.append({
        "ts": int(datetime.now(JST).timestamp()),
        "to": to_addr,
        "amount_usd": amount,
        "tx_hash": tx,
        "wallet_usd_before": wallet_usd,
    })
    save_sent(entries)

    mail_ok = send_receipt_mail(to_addr, amount, tx) if tx else False
    print(json.dumps({"action": "sent" if tx else "send-failed",
                      "to": to_addr, "amount_usd": amount,
                      "tx_hash": tx, "mail_sent": mail_ok},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
