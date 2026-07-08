#!/usr/bin/env python3
"""run.py -- chains withdraw.py -> bridge.py -> send_to_franklin.py as ONE pipeline (§2 of
docs/loop-engineering/11-parent-funding-loop.md). Each step's own money-safety rails (caps,
identity, kill-switch, on-chain confirmation, ledger) are unchanged -- this is only a
convenience wrapper; it stops at the first step that does not return `ok: true` (fail-closed,
never continues to bridge/send money that wasn't actually confirmed).

This file intentionally contains NO funding decision logic (no "is Franklin starving?"
judgment) -- that is the separate OBSERVE/DECIDE loop described in the parent spec, out of
scope for this mechanism-only build. This just runs the three mechanical steps in order.

Usage: python3 run.py --dry [--amount-usd X]
       python3 run.py       [--amount-usd X]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# withdraw.py needs the `polymarket` SDK, which only lives in the polymarket-agent's own venv
# (see skills/earn/polymarket-trade/run.sh's own `$AGENT_HOME/.venv/bin/python` convention).
# bridge.py/send_to_franklin.py need `solders` + the base web3/eth_account/requests stack,
# which are present in the system python3 (verified live) but NOT in that narrower venv --
# so each step is dispatched with the interpreter that actually has its dependencies,
# overridable via env for a different machine layout.
WITHDRAW_PYTHON = os.environ.get(
    "WITHDRAW_PYTHON",
    os.path.expanduser("~/.anicca-founder/agents/polymarket-agent/.venv/bin/python3"),
)
DEFAULT_PYTHON = os.environ.get("FUNDING_PYTHON", "python3")

PYTHON_FOR_SCRIPT = {
    "withdraw.py": WITHDRAW_PYTHON,
    "bridge.py": DEFAULT_PYTHON,
    "send_to_franklin.py": DEFAULT_PYTHON,
}


def _run(script: str, dry: bool, amount_usd: float | None, extra_args: list[str] | None = None) -> dict:
    python_bin = PYTHON_FOR_SCRIPT.get(script, DEFAULT_PYTHON)
    cmd = [python_bin, str(HERE / script)]
    if dry:
        cmd.append("--dry")
    if amount_usd is not None:
        cmd += ["--amount-usd", str(amount_usd)]
    cmd += extra_args or []
    proc = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception:
        return {"ok": False, "error": f"unparseable output from {script}", "raw_stdout": proc.stdout, "raw_stderr": proc.stderr[-2000:]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    parser.add_argument("--amount-usd", type=float, default=None)
    parser.add_argument(
        "--include-pusd",
        action="store_true",
        help="also unwrap pUSD -> USDC.e in the withdraw step (needed whenever the deposit "
        "wallet's balance is mostly/entirely pUSD, which is the common case -- pm-earner "
        "trades in pUSD, not raw USDC.e)",
    )
    args = parser.parse_args()

    results = {}

    withdraw_extra = ["--include-pusd"] if args.include_pusd else []
    results["withdraw"] = _run("withdraw.py", args.dry, args.amount_usd, withdraw_extra)
    print(json.dumps({"step": "withdraw", "result": results["withdraw"]}))
    if not results["withdraw"].get("ok"):
        print(json.dumps({"ok": False, "pipeline": "stopped at withdraw", "results": results}))
        sys.exit(1)

    results["bridge"] = _run("bridge.py", args.dry, args.amount_usd)
    print(json.dumps({"step": "bridge", "result": results["bridge"]}))
    if not results["bridge"].get("ok"):
        print(json.dumps({"ok": False, "pipeline": "stopped at bridge", "results": results}))
        sys.exit(1)

    results["send_to_franklin"] = _run("send_to_franklin.py", args.dry, args.amount_usd)
    print(json.dumps({"step": "send_to_franklin", "result": results["send_to_franklin"]}))
    if not results["send_to_franklin"].get("ok"):
        print(json.dumps({"ok": False, "pipeline": "stopped at send_to_franklin", "results": results}))
        sys.exit(1)

    print(json.dumps({"ok": True, "pipeline": "complete", "results": results}))


if __name__ == "__main__":
    main()
