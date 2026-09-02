#!/usr/bin/env python3
"""One finite Alpaca investment pass."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from allocator import build_candidates, choose, order_for
from alpaca_cli import (find_order_by_client_id, observe, read_allocator_snapshot,
                        read_campaign_snapshot, submit_order)
from campaign import SYMBOLS, reconcile
from effect_store import mark_started, reconcile_started, record_no_trade, seal


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def main() -> int:
    state = Path(os.environ.get(
        "ALPACA_INVESTMENT_STATE_DIR",
        "~/.local/state/life-manager/alpaca-investment",
    )).expanduser()
    try:
        credentials_path = Path(os.environ.get(
            "ANICCA_CREDENTIALS_FILE",
            "~/.local/share/anicca/credentials.json",
        )).expanduser()
        cli_path = Path(os.environ.get("ALPACA_CLI", "~/.local/bin/alpaca")).expanduser()
        reconciliation = reconcile_started(
            state / "receipts.jsonl",
            lambda client_order_id: find_order_by_client_id(
                credentials_path=credentials_path,
                cli_path=cli_path,
                client_order_id=client_order_id,
            ),
        )
        observation = observe(
            credentials_path=credentials_path,
            cli_path=cli_path,
        )
        campaign = reconcile(read_campaign_snapshot(
            credentials_path=credentials_path,
            cli_path=cli_path,
            symbols=SYMBOLS,
        ))
        allocator_snapshot = read_allocator_snapshot(
            credentials_path=credentials_path, cli_path=cli_path)
        candidates = build_candidates(allocator_snapshot)
        decision = choose(
            allocator_snapshot, candidates, state,
            Path(__file__).resolve().parents[2] / "runtime/agent-runner/agent_runner.py",
            Path(__file__).resolve().parents[2],
        )
        effect = "none"
        if decision["approved"]:
            order = order_for(decision)
            sealed = seal(state / "receipts.jsonl", decision, order)
            mark_started(state / "receipts.jsonl", sealed)
            submit_order(credentials_path=credentials_path, cli_path=cli_path,
                         client_order_id=sealed["client_order_id"], order=order)
            reconcile_started(
                state / "receipts.jsonl",
                lambda value: find_order_by_client_id(
                    credentials_path=credentials_path, cli_path=cli_path, client_order_id=value),
            )
            effect = sealed["effect_id"]
        else:
            record_no_trade(state / "receipts.jsonl", decision)
        _atomic_json(state / "allocation-latest.json", decision)
        _atomic_json(state / "observation-latest.json", observation)
        _atomic_json(state / "campaign.json", campaign)
        summary = {
            "account": observation["account"],
            "activities_count": observation["activities_count"],
            "candidate_count": len(candidates),
            "decision": decision["candidate_ref"],
            "effect": effect,
            "exit_status": campaign["exit_status"],
            "loop_id": "alpaca-investment",
            "orders_count": observation["open_and_closed_orders_count"],
            "paper": True,
            "positions_count": len(observation["positions"]),
            "unrealized_pnl_usd": campaign["unrealized_pnl_usd"],
            "reconciliation": reconciliation,
            "status": "allocated",
        }
        print(json.dumps(summary, separators=(",", ":")))
        return 0
    except (OSError, subprocess.SubprocessError, ValueError, json.JSONDecodeError):
        print(json.dumps({
            "blocker": "alpaca_pass_failed",
            "effect": "none",
            "loop_id": "alpaca-investment",
            "status": "blocked",
        }, separators=(",", ":")))
        return 78


if __name__ == "__main__":
    raise SystemExit(main())
