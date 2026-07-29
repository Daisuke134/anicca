#!/usr/bin/env python3
"""bridge.py -- §2 step 2 of the funding mechanism: Polygon USDC.e (owner EOA 0x810f) ->
Solana USDC (founder Solana wallet BF9v). Reuses the EXACT relay.link quote+execute flow
already proven live elsewhere in this repo:
  - skills/earn/hl-trade/fund-hl.mjs   (Base -> Hyperliquid, same-owner cross-chain deposit)
  - skills/earn/sol-to-usdc.py         (Solana -> Base, opposite direction)
  - docs/loop-engineering/10-STATUS-verified.md TODO#2: "bridge=relay.link 実証済
    ($10 Polygon→Solana=$9.95着, 0.46%)" -- this exact Polygon->Solana leg was already quoted
    live before this script existed.

Both ends are owned by the SAME instance (claude-p): origin signer = 0x810f (Polygon), and
recipient = BF9v (Solana), so no destination-side signature is required (relay's solvers
credit the destination chain once the origin-chain tx lands, exactly like the fund-hl.mjs
precedent) -- only the Polygon-side transactions need signing, via web3.py (already used
this way in skills/self/spawn/scripts/seed-child.py for a plain EVM transfer).

Usage:
  python3 bridge.py --dry [--amount-usd X]     # quote only, no signing, no broadcast
  python3 bridge.py       [--amount-usd X]     # REAL bridge (signs + sends Polygon txs)

Env: POLYGON_WALLET_PRIVATE_KEY (falls back to PM_TRADE_AGENT_HOME/.env, same key as
withdraw.py -- it is the SAME owner EOA 0x810f), POLYGON_RPC_URL, FOUNDER_SOLANA_WALLET_JSON
(default ~/.anicca-founder/solana-wallet.json).

Output: exactly one JSON line on stdout.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from lib.caps import check_caps, reserve_protected_amount  # noqa: E402
from lib.erc20 import erc20_balance_units, eth_tx_confirmed_success  # noqa: E402
from lib.identity import verify_evm_address, verify_solana_secret_file  # noqa: E402
from lib.kill_switch import is_killed  # noqa: E402
from lib.ledger import append_ledger, build_row, read_ledger  # noqa: E402

CONFIG = json.load(open(os.path.join(HERE, "config.json")))
REPO_ROOT = Path(os.environ.get("LIFE_MANAGER_REPO", Path(__file__).resolve().parents[3]))
LEDGER_PATH = str(REPO_ROOT / "skills/earn/state/funding-ledger.jsonl")
AGENT_HOME = os.environ.get(
    "PM_TRADE_AGENT_HOME", os.path.expanduser("~/.anicca-founder/agents/polymarket-agent")
)
POLYGON_RPC = os.environ.get("POLYGON_RPC_URL", CONFIG["rpc"]["polygon"])
FOUNDER_SOLANA_WALLET_JSON = os.environ.get(
    "FOUNDER_SOLANA_WALLET_JSON", os.path.expanduser("~/.anicca-founder/solana-wallet.json")
)

USDCE = CONFIG["tokens"]["usdce_polygon"]
USDC_SOLANA_MINT = CONFIG["tokens"]["usdc_solana_mint"]
OWNER_EOA = CONFIG["known_addresses"]["owner_eoa_polygon"]
FOUNDER_SOLANA = CONFIG["known_addresses"]["founder_solana"]
POLYGON_CHAIN_ID = CONFIG["chain_ids"]["polygon"]
SOLANA_CHAIN_ID = CONFIG["chain_ids"]["solana"]
MAX_FEE_PCT = CONFIG["bridge_max_fee_pct"]


def _load_key() -> str:
    key = os.environ.get("POLYGON_WALLET_PRIVATE_KEY")
    if not key:
        from dotenv import dotenv_values

        env = dotenv_values(os.path.join(AGENT_HOME, ".env"))
        key = env.get("POLYGON_WALLET_PRIVATE_KEY")
    if not key:
        raise RuntimeError("POLYGON_WALLET_PRIVATE_KEY not found (env or agent .env)")
    return key if key.startswith("0x") else "0x" + key


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true", default=os.environ.get("DRY") == "1")
    parser.add_argument("--amount-usd", type=float, default=None)
    args = parser.parse_args()

    def fail(reason: str, extra: dict | None = None) -> None:
        row = build_row(
            step="bridge", amount_usd=args.amount_usd or 0, status="failed", reason=reason, extra=extra or {}
        )
        append_ledger(LEDGER_PATH, row)
        print(json.dumps({"ok": False, "step": "bridge", "error": reason}))
        sys.exit(1)

    if is_killed(HERE):
        fail("kill-switch present")
        return

    from eth_account import Account

    key = _load_key()
    acct = Account.from_key(key)
    signer_check = verify_evm_address(candidate=acct.address, known_address=OWNER_EOA)
    if not signer_check["verified"]:
        fail(f"signer identity mismatch: {signer_check['reason']}")
        return

    recipient_check = verify_solana_secret_file(
        path=FOUNDER_SOLANA_WALLET_JSON, known_address=FOUNDER_SOLANA
    )
    if not recipient_check["verified"]:
        fail(f"recipient identity mismatch: {recipient_check['reason']}")
        return

    balance_units = erc20_balance_units(POLYGON_RPC, USDCE, acct.address)
    balance_usd = balance_units / 1e6
    withdrawable_usd = reserve_protected_amount(available_usd=balance_usd, reserve_usd=0.0)
    amount_usd = args.amount_usd if args.amount_usd is not None else withdrawable_usd
    amount_usd = round(min(amount_usd, withdrawable_usd), 6)

    if amount_usd <= 0:
        fail("no USDC.e balance available to bridge", {"balance_usd": balance_usd})
        return

    history = read_ledger(LEDGER_PATH)
    # bridge moves already-withdrawn (already-cap-counted) money across chains — not a new
    # outflow of claude-p capital, so it must not re-consume the daily/cumulative cap.
    decision = check_caps(amount_usd=amount_usd, history=history, config=CONFIG, now_ts=time.time(), counts_as_outflow=False)
    if not decision.allowed:
        fail(decision.reason, {"balance_usd": balance_usd, "amount_usd": amount_usd})
        return

    amount_units = int(round(amount_usd * 1e6))
    quote = requests.post(
        "https://api.relay.link/quote",
        json={
            "user": acct.address,
            "recipient": FOUNDER_SOLANA,
            "originChainId": POLYGON_CHAIN_ID,
            "destinationChainId": SOLANA_CHAIN_ID,
            "originCurrency": USDCE,
            "destinationCurrency": USDC_SOLANA_MINT,
            "amount": str(amount_units),
            "tradeType": "EXACT_INPUT",
        },
        timeout=30,
    ).json()

    details = quote.get("details") or {}
    if not details:
        fail("relay quote failed", {"raw": str(quote)[:300]})
        return

    in_usd = float((details.get("currencyIn") or {}).get("amountUsd") or amount_usd)
    out_usd = float((details.get("currencyOut") or {}).get("amountUsd") or 0)
    fee_usd = max(0.0, in_usd - out_usd)
    fee_pct = (fee_usd / in_usd * 100) if in_usd > 0 else 100.0

    plan = {
        "amount_usd": amount_usd,
        "in_usd": in_usd,
        "out_usd": out_usd,
        "fee_usd": round(fee_usd, 6),
        "fee_pct": round(fee_pct, 3),
        "sender": acct.address,
        "recipient": FOUNDER_SOLANA,
    }

    if fee_pct > MAX_FEE_PCT:
        fail(f"uneconomic bridge: fee {fee_pct:.1f}% > cap {MAX_FEE_PCT}%", plan)
        return

    if args.dry:
        row = build_row(
            step="bridge",
            amount_usd=amount_usd,
            status="dry",
            reason="dry-run: quote only, no signing/broadcast",
            from_addr=acct.address,
            to_addr=FOUNDER_SOLANA,
            extra={"plan": plan},
        )
        append_ledger(LEDGER_PATH, row)
        print(json.dumps({"ok": True, "dry": True, "step": "bridge", "plan": plan}))
        return

    from web3 import Web3

    w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))
    hashes = []
    for step in quote.get("steps") or []:
        for item in step.get("items") or []:
            tx = item.get("data") or {}
            if not tx.get("to"):
                continue
            built = {
                "from": acct.address,
                "to": Web3.to_checksum_address(tx["to"]),
                "data": tx.get("data", "0x"),
                "value": int(tx.get("value") or 0),
                "nonce": w3.eth.get_transaction_count(acct.address),
                "chainId": POLYGON_CHAIN_ID,
                "gas": int(tx["gas"], 16) if isinstance(tx.get("gas"), str) else (tx.get("gas") or 300000),
                "maxFeePerGas": w3.eth.gas_price * 2,
                "maxPriorityFeePerGas": w3.to_wei(30, "gwei"),
            }
            signed = w3.eth.account.sign_transaction(built, key)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction).hex()
            tx_hash = tx_hash if tx_hash.startswith("0x") else "0x" + tx_hash

            # Finding A fix (money-safety adversary review, 2026-07-08): the tx is ALREADY
            # broadcast at this point (send_raw_transaction returned its hash) -- record a
            # 'pending' row with that hash BEFORE waiting for the receipt. This was previously
            # the WEAKEST instance of Finding A (no try/except at all around this entire
            # broadcast loop): if wait_for_transaction_receipt/eth_tx_confirmed_success below
            # raised (timeout, rate limit, transient RPC failure), the script crashed with no
            # ledger row written at all for a real, already-broadcast transfer.
            append_ledger(LEDGER_PATH, build_row(
                step="bridge",
                amount_usd=amount_usd,
                status="pending",
                reason="tx broadcast, awaiting on-chain confirmation",
                tx_hash=tx_hash,
                from_addr=acct.address,
                to_addr=FOUNDER_SOLANA,
                extra={"plan": plan, "hashes": hashes},
            ))
            try:
                w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
                tx_confirmed = eth_tx_confirmed_success(POLYGON_RPC, tx_hash)
            except Exception as exc:
                # Confirmation RPC itself failed -- the pending row above already preserved
                # the audit trail; do not append a second, possibly-wrong-status row for the
                # same tx_hash (a human/agent can look it up on-chain later for reconciliation).
                print(json.dumps({
                    "ok": False,
                    "step": "bridge",
                    "error": f"tx {tx_hash} broadcast but confirmation check raised: {exc} -- "
                    "needs manual reconciliation (see pending ledger row)",
                    "hashes": hashes,
                    "tx_hash": tx_hash,
                }))
                sys.exit(1)
            if not tx_confirmed:
                row = build_row(
                    step="bridge",
                    amount_usd=amount_usd,
                    status="failed",
                    reason=f"origin tx {tx_hash} did not confirm status=0x1",
                    tx_hash=tx_hash,
                    from_addr=acct.address,
                    to_addr=FOUNDER_SOLANA,
                    extra={"plan": plan, "hashes": hashes},
                )
                append_ledger(LEDGER_PATH, row)
                print(json.dumps({"ok": False, "step": "bridge", "error": row["reason"], "hashes": hashes}))
                sys.exit(1)
            hashes.append(tx_hash)

    row = build_row(
        step="bridge",
        amount_usd=amount_usd,
        status="sent",
        reason="origin-chain tx(s) confirmed on-chain; destination credit handled by relay solver",
        tx_hash=hashes[-1] if hashes else None,
        from_addr=acct.address,
        to_addr=FOUNDER_SOLANA,
        extra={"plan": plan, "hashes": hashes},
    )
    append_ledger(LEDGER_PATH, row)
    print(json.dumps({"ok": True, "step": "bridge", "hashes": hashes, "amount_usd": amount_usd, "plan": plan}))


if __name__ == "__main__":
    main()
