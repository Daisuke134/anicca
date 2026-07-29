#!/usr/bin/env python3
"""send_to_franklin.py -- §2 step 3 of the funding mechanism: Solana USDC (founder wallet
BF9v) -> Franklin (8Fpqd) SPL transfer. Generalizes the `spawn-auto-seed` pattern (real
on-chain transfer, tx hash recorded, ledger row, NO human instruction --
.vcsdd/features/spawn-auto-seed/spec/behavioral-spec.md REQ-4/REQ-6) from a plain Base USDC
EOA transfer (seed-child.py) to a Solana SPL token transfer, via the official `spl-token` CLI
(lib/solana_cli.py).

MONEY-SAFETY (the Efpap5-incident fix, docs/loop-engineering/11-parent-funding-loop.md §3):
the recipient is NEVER a hardcoded/display address alone -- this script derives the pubkey
Franklin's OWN `~/.blockrun/.solana-session` key file ACTUALLY produces and requires it to
equal the known-good address before ANY transfer is attempted. This is the direct fix for
docs/loop-engineering/10-STATUS-verified.md's TODO#2 note: "franklin proxy 直近再起動で wallet
を `8Fpqd` でなく `Efpap5` 表示 = identity 要確認". No flag exists to bypass this check.

Usage:
  python3 send_to_franklin.py --dry [--amount-usd X]     # no CLI subprocess invoked
  python3 send_to_franklin.py       [--amount-usd X]     # REAL SPL transfer

Env: FOUNDER_SOLANA_WALLET_JSON (default ~/.anicca-founder/solana-wallet.json),
     FRANKLIN_SESSION_PATH (default ~/.blockrun/.solana-session), SOLANA_RPC_URL.
Output: exactly one JSON line on stdout.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from lib.caps import check_caps, reserve_protected_amount  # noqa: E402
from lib.identity import verify_solana_secret_file  # noqa: E402
from lib.kill_switch import is_killed  # noqa: E402
from lib.ledger import append_ledger, build_row, read_ledger  # noqa: E402
from lib.solana_cli import spl_transfer  # noqa: E402
from lib.solana_rpc import confirmed_success, spl_token_balance_units  # noqa: E402

CONFIG = json.load(open(os.path.join(HERE, "config.json")))
REPO_ROOT = Path(os.environ.get("LIFE_MANAGER_REPO", Path(__file__).resolve().parents[3]))
LEDGER_PATH = str(REPO_ROOT / "skills/earn/state/funding-ledger.jsonl")
FOUNDER_SOLANA_WALLET_JSON = os.environ.get(
    "FOUNDER_SOLANA_WALLET_JSON", os.path.expanduser("~/.anicca-founder/solana-wallet.json")
)
FRANKLIN_SESSION_PATH = os.environ.get(
    "FRANKLIN_SESSION_PATH", os.path.expanduser("~/.blockrun/.solana-session")
)
SOLANA_RPC = os.environ.get("SOLANA_RPC_URL", CONFIG["rpc"]["solana"])

USDC_MINT = CONFIG["tokens"]["usdc_solana_mint"]
FOUNDER_SOLANA = CONFIG["known_addresses"]["founder_solana"]
FRANKLIN_SOLANA = CONFIG["known_addresses"]["franklin_solana"]


def _load_sender_secret() -> str:
    with open(FOUNDER_SOLANA_WALLET_JSON, "r", encoding="utf-8") as f:
        raw = f.read().strip()
    if raw.startswith("{"):
        return json.loads(raw)["secret_key_base58"]
    return raw


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true", default=os.environ.get("DRY") == "1")
    parser.add_argument("--amount-usd", type=float, default=None)
    args = parser.parse_args()

    def fail(reason: str, extra: dict | None = None) -> None:
        row = build_row(
            step="send_to_franklin",
            amount_usd=args.amount_usd or 0,
            status="failed",
            reason=reason,
            extra=extra or {},
        )
        append_ledger(LEDGER_PATH, row)
        print(json.dumps({"ok": False, "step": "send_to_franklin", "error": reason}))
        sys.exit(1)

    if is_killed(HERE):
        fail("kill-switch present")
        return

    # Sender identity: confirm OUR own key file really derives BF9v (defense in depth --
    # never spend from a wallet file that doesn't actually produce the address we think it does).
    sender_check = verify_solana_secret_file(
        path=FOUNDER_SOLANA_WALLET_JSON, known_address=FOUNDER_SOLANA
    )
    if not sender_check["verified"]:
        fail(f"sender identity mismatch: {sender_check['reason']}")
        return

    # Recipient identity: THE Efpap5-incident fix. Franklin's own session file must derive
    # the known 8Fpqd address, or we do not send -- no override exists for this check.
    recipient_check = verify_solana_secret_file(
        path=FRANKLIN_SESSION_PATH, known_address=FRANKLIN_SOLANA
    )
    if not recipient_check["verified"]:
        fail(f"recipient identity mismatch (Efpap5-incident guard): {recipient_check['reason']}")
        return

    balance_units = spl_token_balance_units(SOLANA_RPC, FOUNDER_SOLANA, USDC_MINT)
    balance_usd = balance_units / 1e6
    withdrawable_usd = reserve_protected_amount(available_usd=balance_usd, reserve_usd=0.0)
    amount_usd = args.amount_usd if args.amount_usd is not None else withdrawable_usd
    amount_usd = round(min(amount_usd, withdrawable_usd), 6)

    if amount_usd <= 0:
        fail("no USDC balance available to send", {"balance_usd": balance_usd})
        return

    history = read_ledger(LEDGER_PATH)
    # send delivers already-withdrawn (already-cap-counted) money to Franklin — not a new
    # outflow of claude-p capital, so it must not re-consume the daily/cumulative cap.
    decision = check_caps(amount_usd=amount_usd, history=history, config=CONFIG, now_ts=time.time(), counts_as_outflow=False)

    plan = {
        "sender": FOUNDER_SOLANA,
        "recipient": FRANKLIN_SOLANA,
        "balance_usd": round(balance_usd, 6),
        "amount_usd": amount_usd,
        "cap_allowed": decision.allowed,
        "cap_reason": decision.reason,
    }

    if not decision.allowed:
        row = build_row(
            step="send_to_franklin",
            amount_usd=amount_usd,
            status="skipped",
            reason=decision.reason,
            from_addr=FOUNDER_SOLANA,
            to_addr=FRANKLIN_SOLANA,
            extra={"plan": plan},
        )
        append_ledger(LEDGER_PATH, row)
        print(json.dumps({"ok": False, "step": "send_to_franklin", "plan": plan, "reason": decision.reason}))
        sys.exit(1)

    if args.dry:
        row = build_row(
            step="send_to_franklin",
            amount_usd=amount_usd,
            status="dry",
            reason="dry-run: no spl-token subprocess invoked",
            from_addr=FOUNDER_SOLANA,
            to_addr=FRANKLIN_SOLANA,
            extra={"plan": plan},
        )
        append_ledger(LEDGER_PATH, row)
        print(json.dumps({"ok": True, "dry": True, "step": "send_to_franklin", "plan": plan}))
        return

    secret = _load_sender_secret()
    result = spl_transfer(
        secret_b58=secret,
        mint=USDC_MINT,
        amount_tokens=amount_usd,
        recipient=FRANKLIN_SOLANA,
        rpc_url=SOLANA_RPC,
    )
    if not result.get("ok") or not result.get("signature"):
        row = build_row(
            step="send_to_franklin",
            amount_usd=amount_usd,
            status="failed",
            reason=f"spl-token transfer failed: {result.get('error') or result.get('raw')}",
            from_addr=FOUNDER_SOLANA,
            to_addr=FRANKLIN_SOLANA,
            extra={"plan": plan},
        )
        append_ledger(LEDGER_PATH, row)
        print(json.dumps({"ok": False, "step": "send_to_franklin", "error": row["reason"]}))
        sys.exit(1)

    signature = result["signature"]

    # Finding A fix (money-safety adversary review, 2026-07-08): by the time spl_transfer()
    # returns ok+signature, the `spl-token transfer` CLI subprocess has ALREADY completed
    # (this is a blocking subprocess.run, not an async handle) -- record a 'pending' row with
    # that signature BEFORE the independent confirmed_success() RPC check below. If that check
    # raises, this pending row is the only evidence this real transfer was broadcast.
    append_ledger(LEDGER_PATH, build_row(
        step="send_to_franklin",
        amount_usd=amount_usd,
        status="pending",
        reason="spl-token transfer completed, awaiting independent on-chain confirmation",
        tx_hash=signature,
        from_addr=FOUNDER_SOLANA,
        to_addr=FRANKLIN_SOLANA,
        extra={"plan": plan},
    ))
    try:
        sig_confirmed = confirmed_success(SOLANA_RPC, signature)
    except Exception as exc:
        # Confirmation RPC itself failed -- the pending row above already preserved the audit
        # trail; do not append a second, possibly-wrong-status row for the same signature (a
        # human/agent can look it up on-chain later for reconciliation).
        print(json.dumps({
            "ok": False,
            "step": "send_to_franklin",
            "error": f"signature {signature} broadcast but confirmation check raised: {exc} -- "
            "needs manual reconciliation (see pending ledger row)",
            "signature": signature,
        }))
        sys.exit(1)

    if not sig_confirmed:
        row = build_row(
            step="send_to_franklin",
            amount_usd=amount_usd,
            status="failed",
            reason=f"signature {signature} did not confirm on-chain",
            tx_hash=signature,
            from_addr=FOUNDER_SOLANA,
            to_addr=FRANKLIN_SOLANA,
            extra={"plan": plan},
        )
        append_ledger(LEDGER_PATH, row)
        print(json.dumps({"ok": False, "step": "send_to_franklin", "error": row["reason"]}))
        sys.exit(1)

    row = build_row(
        step="send_to_franklin",
        amount_usd=amount_usd,
        status="sent",
        reason="confirmed on-chain",
        tx_hash=signature,
        from_addr=FOUNDER_SOLANA,
        to_addr=FRANKLIN_SOLANA,
        extra={"plan": plan},
    )
    append_ledger(LEDGER_PATH, row)
    print(json.dumps({"ok": True, "step": "send_to_franklin", "signature": signature, "amount_usd": amount_usd, "plan": plan}))


if __name__ == "__main__":
    main()
