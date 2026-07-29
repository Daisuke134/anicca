#!/usr/bin/env python3
"""withdraw.py -- §2 step 1 of the funding mechanism (the one genuine gap identified in
docs/loop-engineering/11-parent-funding-loop.md): move claude-p's surplus USDC.e out of the
Polymarket deposit wallet (0x904B..., an ERC-1967/POLY_1271 proxy owned by the EOA that signs
its orders) to that SAME owner EOA (0x810f... on Polygon).

RESEARCH FINDING (2026-07-08, verified two independent ways -- see report):
  1. Official docs (https://docs.polymarket.com/trading/deposit-wallets, "Mental Model" +
     "Execute a Wallet Batch"): the deposit wallet owner signs a `WALLET` relayer batch (a
     normal EIP-712 signature, NOT the POLY_1271 order-signing path) to execute ANY on-chain
     call from the deposit wallet, including a plain ERC-20 transfer to an arbitrary address.
  2. Installed SDK (`polymarket` package, `~/.anicca-founder/agents/polymarket-agent/.venv`):
     `SecureClient.transfer_erc20(token_address, recipient_address, amount)` is EXACTLY that
     WALLET-batch ERC-20 transfer, already used (with recipient = a bridge address) by this
     repo's own `fund_via_bridge.py`. Pointing `recipient_address` at our OWN owner EOA
     (0x810f) instead of a bridge address is a withdrawal -- no new mechanism is needed, and
     no browser/human credential is involved.

This script defaults to withdrawing already-unwrapped USDC.e sitting in the deposit wallet
(no extra step needed -- `transfer_erc20` handles any ERC-20). Optionally (`--include-pusd`)
it will also unwrap pUSD -> USDC.e first via the CollateralOfframp contract
(https://docs.polymarket.com/concepts/pusd, "Unwrapping"), built as a raw `TransactionCall`
(same primitive `erc20_transfer_call`/`erc20_approval_call` already use internally) and
dispatched via `SecureClient._dispatch_single_call` -- the SDK does not expose a named
`unwrap()` helper, so this one call uses the same low-level primitive the SDK's own named
helpers are built from, not a hand-rolled raw transaction from scratch.

Usage:
  python3 withdraw.py --dry [--amount-usd X] [--include-pusd]
  python3 withdraw.py       [--amount-usd X] [--include-pusd]      # REAL transfer

Env:
  PM_TRADE_AGENT_HOME   default ~/.anicca-founder/agents/polymarket-agent (reads its .env for
                        POLYGON_WALLET_PRIVATE_KEY, exactly like place_order.py/fund_via_bridge.py)
  POLYGON_RPC_URL       default from config.json rpc.polygon

Output: exactly one JSON line on the real stdout (clean-stdout guarantee, same pattern as
place_order.py -- the polymarket SDK can print during import/mint, so all of that is
redirected to stderr and only the final result is ever written to the captured real stdout).
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import time
from pathlib import Path

_REAL_STDOUT = sys.stdout  # capture BEFORE any import that might print


def _emit(obj: dict) -> None:
    print(json.dumps(obj), file=_REAL_STDOUT, flush=True)


HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = Path(os.environ.get("LIFE_MANAGER_REPO", Path(__file__).resolve().parents[3]))
POLYMARKET_TRADE_DIR = str(REPO_ROOT / "skills/earn/polymarket-trade")
sys.path.insert(0, HERE)
sys.path.insert(0, POLYMARKET_TRADE_DIR)  # reuse client_for/is_registered/relayer_auth, no dup

from lib.caps import check_caps, reserve_protected_amount  # noqa: E402
from lib.erc20 import erc20_balance_units, eth_tx_confirmed_success  # noqa: E402
from lib.identity import verify_evm_address  # noqa: E402
from lib.kill_switch import is_killed  # noqa: E402
from lib.ledger import append_ledger, build_row, read_ledger  # noqa: E402

CONFIG = json.load(open(os.path.join(HERE, "config.json")))
LEDGER_PATH = str(REPO_ROOT / "skills/earn/state/funding-ledger.jsonl")
AGENT_HOME = os.environ.get("PM_TRADE_AGENT_HOME", os.path.expanduser("~/.anicca-founder/agents/polymarket-agent"))
POLYGON_RPC = os.environ.get("POLYGON_RPC_URL", CONFIG["rpc"]["polygon"])

PUSD = CONFIG["tokens"]["pusd_polygon"]
USDCE = CONFIG["tokens"]["usdce_polygon"]
OFFRAMP = CONFIG["tokens"]["collateral_offramp_polygon"]
OWNER_EOA = CONFIG["known_addresses"]["owner_eoa_polygon"]
DEPOSIT_WALLET = CONFIG["known_addresses"]["pm_deposit_wallet"]


def fail(reason: str) -> None:
    _emit({"ok": False, "step": "withdraw", "error": reason})
    sys.exit(1)


def _unwrap_call(asset: str, to: str, amount_units: int):
    """Build the CollateralOfframp.unwrap(address,address,uint256) call using the SAME
    encoding primitives the SDK's own erc20_transfer_call/erc20_approval_call use (keccak
    selector + eth_abi encode) -- see docs/concepts/pusd "Unwrapping" for the signature."""
    from eth_abi.abi import encode as abi_encode
    from eth_utils.crypto import keccak
    from polymarket._internal.actions.relayer.calls import TransactionCall

    selector = keccak(b"unwrap(address,address,uint256)")[:4]
    payload = selector + abi_encode(["address", "address", "uint256"], [asset, to, amount_units])
    return TransactionCall(to=OFFRAMP, data="0x" + payload.hex())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true", default=os.environ.get("DRY") == "1")
    parser.add_argument("--amount-usd", type=float, default=None)
    parser.add_argument("--include-pusd", action="store_true")
    args = parser.parse_args()

    if is_killed(HERE):
        row = build_row(step="withdraw", amount_usd=0, status="skipped", reason="kill-switch present")
        append_ledger(LEDGER_PATH, row)
        _emit({"ok": False, "step": "withdraw", "error": "kill-switch present"})
        sys.exit(1)

    with contextlib.redirect_stdout(sys.stderr):
        from dotenv import load_dotenv

        load_dotenv(os.path.join(AGENT_HOME, ".env"))
        key = os.environ.get("POLYGON_WALLET_PRIVATE_KEY")
        if not key:
            fail("POLYGON_WALLET_PRIVATE_KEY not set in agent .env")
        key = key if key.startswith("0x") else "0x" + key

        from eth_account import Account

        acct = Account.from_key(key)
        signer_check = verify_evm_address(candidate=acct.address, known_address=OWNER_EOA)
        if not signer_check["verified"]:
            fail(f"signer identity mismatch: {signer_check['reason']}")

        from fund_via_bridge import client_for, is_registered  # reuse, no duplicate impl

        client, _ = client_for(key)
        deposit_wallet = str(client._ctx.wallet)
        deposit_check = verify_evm_address(candidate=deposit_wallet, known_address=DEPOSIT_WALLET)
        if not deposit_check["verified"]:
            fail(f"deposit wallet identity mismatch (proxy banner distrust rail): {deposit_check['reason']}")

        if not is_registered(client):
            fail("deposit wallet not registered with Polymarket relayer -- nothing safe to withdraw")

        usdce_units = erc20_balance_units(POLYGON_RPC, USDCE, deposit_wallet)
        pusd_units = 0
        try:
            ba = client.get_balance_allowance(asset_type="COLLATERAL")
            pusd_units = int(getattr(ba, "balance", 0) or 0)
        except Exception:
            pusd_units = 0

        usdce_usd = usdce_units / 1e6
        pusd_usd = pusd_units / 1e6
        available_usd = usdce_usd + (pusd_usd if args.include_pusd else 0.0)

    withdrawable_usd = reserve_protected_amount(
        available_usd=available_usd, reserve_usd=CONFIG["reserve_usd"]
    )
    amount_usd = args.amount_usd if args.amount_usd is not None else withdrawable_usd
    amount_usd = min(amount_usd, withdrawable_usd)
    amount_usd = round(amount_usd, 6)

    history = read_ledger(LEDGER_PATH)
    decision = check_caps(amount_usd=amount_usd, history=history, config=CONFIG, now_ts=time.time())

    plan = {
        "deposit_wallet": deposit_wallet,
        "owner_eoa": OWNER_EOA,
        "usdce_balance_usd": round(usdce_usd, 6),
        "pusd_balance_usd": round(pusd_usd, 6),
        "reserve_usd": CONFIG["reserve_usd"],
        "withdrawable_usd": round(withdrawable_usd, 6),
        "amount_usd": amount_usd,
        "cap_allowed": decision.allowed,
        "cap_reason": decision.reason,
    }

    if not decision.allowed or amount_usd <= 0:
        row = build_row(
            step="withdraw",
            amount_usd=amount_usd,
            status="skipped",
            reason=decision.reason if not decision.allowed else "amount_usd <= 0 after reserve protection",
            from_addr=deposit_wallet,
            to_addr=OWNER_EOA,
            extra={"plan": plan},
        )
        append_ledger(LEDGER_PATH, row)
        _emit({"ok": False, "step": "withdraw", "plan": plan, "reason": row["reason"]})
        sys.exit(1 if not args.dry else 0)

    if args.dry:
        row = build_row(
            step="withdraw",
            amount_usd=amount_usd,
            status="dry",
            reason="dry-run: no on-chain transfer executed",
            from_addr=deposit_wallet,
            to_addr=OWNER_EOA,
            extra={"plan": plan},
        )
        append_ledger(LEDGER_PATH, row)
        _emit({"ok": True, "dry": True, "step": "withdraw", "plan": plan})
        return

    with contextlib.redirect_stdout(sys.stderr):
        amount_units = int(round(amount_usd * 1e6))
        used_pusd_units = 0
        if amount_units > usdce_units and args.include_pusd:
            shortfall = amount_units - usdce_units
            used_pusd_units = min(shortfall, pusd_units)
            client.approve_erc20(token_address=PUSD, spender_address=OFFRAMP, amount="max")
            unwrap_handle = client._dispatch_single_call(
                _unwrap_call(USDCE, deposit_wallet, used_pusd_units),
                metadata=f"unwrap {used_pusd_units} pUSD -> USDC.e",
            )
            # Finding A fix (money-safety adversary review, 2026-07-08): the unwrap tx is
            # already submitted to the relayer the instant _dispatch_single_call() returns
            # (prepare_gasless_transaction_sync submits before constructing the handle --
            # .wait() only polls for the terminal outcome), so record a 'pending' row with
            # whatever identifier is available BEFORE waiting. If the wait/confirm call below
            # raises, this pending row is the only evidence the unwrap tx exists at all.
            unwrap_hash = unwrap_handle.transaction_hash
            unwrap_tx_id = unwrap_handle.transaction_id
            append_ledger(LEDGER_PATH, build_row(
                step="withdraw",
                amount_usd=amount_usd,
                status="pending",
                reason="unwrap tx submitted, awaiting on-chain confirmation",
                tx_hash=unwrap_hash,
                from_addr=deposit_wallet,
                to_addr=OFFRAMP,
                extra={"plan": plan, "phase": "unwrap", "relayer_transaction_id": unwrap_tx_id},
            ))
            try:
                unwrap_outcome = unwrap_handle.wait()
                unwrap_confirmed = eth_tx_confirmed_success(POLYGON_RPC, unwrap_outcome.transaction_hash)
            except Exception as exc:
                # Confirmation RPC itself failed -- the pending row above already preserved
                # the audit trail; do not append a second, possibly-wrong-status row for the
                # same tx (a human/agent can look it up on-chain later for reconciliation).
                fail(
                    f"unwrap tx {unwrap_hash or unwrap_tx_id} submitted but confirmation check "
                    f"raised: {exc} -- needs manual reconciliation (see pending ledger row)"
                )
            if not unwrap_confirmed:
                append_ledger(LEDGER_PATH, build_row(
                    step="withdraw",
                    amount_usd=amount_usd,
                    status="failed",
                    reason=f"unwrap tx {unwrap_outcome.transaction_hash} did not confirm status=0x1",
                    tx_hash=unwrap_outcome.transaction_hash,
                    from_addr=deposit_wallet,
                    to_addr=OFFRAMP,
                    extra={"plan": plan, "phase": "unwrap"},
                ))
                fail(f"unwrap tx {unwrap_outcome.transaction_hash} did not confirm status=0x1")

        transfer_units = min(amount_units, usdce_units + used_pusd_units)
        handle = client.transfer_erc20(
            token_address=USDCE,
            recipient_address=OWNER_EOA,
            amount=transfer_units,
        )
        # Finding A fix: same reasoning as the unwrap dispatch above -- the transfer is
        # already submitted by the time `handle` is returned, so record a 'pending' row with
        # whatever identifier is available BEFORE waiting for the terminal outcome.
        transfer_hash = handle.transaction_hash
        transfer_tx_id = handle.transaction_id
        append_ledger(LEDGER_PATH, build_row(
            step="withdraw",
            amount_usd=amount_usd,
            status="pending",
            reason="transfer tx submitted, awaiting on-chain confirmation",
            tx_hash=transfer_hash,
            from_addr=deposit_wallet,
            to_addr=OWNER_EOA,
            extra={"plan": plan, "relayer_transaction_id": transfer_tx_id},
        ))
        try:
            outcome = handle.wait()
            tx_hash = outcome.transaction_hash
            confirmed = eth_tx_confirmed_success(POLYGON_RPC, tx_hash)
        except Exception as exc:
            fail(
                f"transfer tx {transfer_hash or transfer_tx_id} submitted but confirmation "
                f"check raised: {exc} -- needs manual reconciliation (see pending ledger row)"
            )

    if not confirmed:
        row = build_row(
            step="withdraw",
            amount_usd=amount_usd,
            status="failed",
            reason=f"tx {tx_hash} did not confirm status=0x1",
            tx_hash=tx_hash,
            from_addr=deposit_wallet,
            to_addr=OWNER_EOA,
            extra={"plan": plan},
        )
        append_ledger(LEDGER_PATH, row)
        fail(f"transfer tx {tx_hash} did not confirm on-chain (status != 0x1)")

    row = build_row(
        step="withdraw",
        amount_usd=amount_usd,
        status="sent",
        reason="confirmed on-chain status=0x1",
        tx_hash=tx_hash,
        from_addr=deposit_wallet,
        to_addr=OWNER_EOA,
        extra={"plan": plan},
    )
    append_ledger(LEDGER_PATH, row)
    _emit({"ok": True, "step": "withdraw", "tx_hash": tx_hash, "amount_usd": amount_usd, "plan": plan})


if __name__ == "__main__":
    main()
