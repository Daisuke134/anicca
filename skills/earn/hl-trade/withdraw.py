#!/usr/bin/env python3
"""withdraw.py — RECOVER-1: withdraw this instance's own Hyperliquid perp-account
balance back to its own address on Arbitrum (HL's `withdraw3` bridge action).

hl.py (account/market/open/close/reconcile) has no withdraw primitive — trading only
opens/closes positions, nothing in this skill ever pulled funds OUT of HL. This is that
missing primitive, built the same way hl.py resolves its signing key (same `_key()`
pattern, GATED per-instance resolution via resolve-identity.mjs, never a hardcoded key).

Mechanism (verified against installed hyperliquid-python-sdk, ground truth):
  `Exchange.withdraw_from_bridge(amount: float, destination: str)` builds the exact
  `{"type": "withdraw3", ...}` action HL's own docs describe (api.hyperliquid.xyz/exchange
  Exchange endpoint, "Initiate a withdrawal request": "$1 fee for withdrawing ... withdrawals
  take approximately 5 minutes to finalize"), signs it, and POSTs it. Destination is HL's own
  L1 bridge -> the SAME address on Arbitrum (HL account address == the EOA), no separate
  Arbitrum address needed.

NO DRY RUN — running `main()` submits a real withdrawal.
"""
import json
import os
import subprocess
import sys

try:
    import eth_account
    from hyperliquid.info import Info
    from hyperliquid.exchange import Exchange
    from hyperliquid.utils import constants
except Exception as e:
    print(json.dumps({"error": "needs hyperliquid-python-sdk + eth_account: " + str(e)[:120]}))
    sys.exit(1)


def _key():
    pkvar = os.environ.get("PKVAR")
    k = (os.environ.get(pkvar) if pkvar else None) or os.environ.get("BLOCKRUN_WALLET_KEY")
    if not k:
        ri = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib", "resolve-identity.mjs")
        try:
            k = subprocess.run(["node", ri, "evm"], capture_output=True, text=True, timeout=10).stdout.strip() or None
        except Exception:
            k = None
    if not k:
        sys.stderr.write("hl-withdraw: no per-instance EVM key resolvable — refusing to sign\n")
        sys.exit(2)
    return k if k.startswith("0x") else "0x" + k


def main():
    w = eth_account.Account.from_key(_key())
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    ex = Exchange(w, constants.MAINNET_API_URL)

    st = info.user_state(w.address)
    withdrawable = float(st.get("withdrawable", 0))
    print(json.dumps({"address": w.address, "withdrawable_before": withdrawable}))

    amount = float(sys.argv[1]) if len(sys.argv) > 1 else withdrawable
    destination = sys.argv[2] if len(sys.argv) > 2 else w.address
    if amount <= 0:
        print(json.dumps({"error": "nothing withdrawable"}))
        return 0
    if amount > withdrawable:
        print(json.dumps({"error": f"requested {amount} exceeds withdrawable {withdrawable}"}))
        return 1

    print(json.dumps({"withdrawing": amount, "destination": destination}))
    result = ex.withdraw_from_bridge(amount, destination)
    print(json.dumps({"result": result}))

    st2 = info.user_state(w.address)
    print(json.dumps({"withdrawable_after": float(st2.get("withdrawable", 0))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
