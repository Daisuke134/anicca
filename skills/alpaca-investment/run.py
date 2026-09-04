#!/usr/bin/env python3
"""One finite Alpaca investment pass."""

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from allocator import build_candidates, choose, order_for
from alpaca_cli import (find_order_by_client_id, observe, read_allocator_snapshot,
                        read_campaign_snapshot, submit_order)
from campaign import CANDIDATE_REF, SYMBOLS, exit_order, reconcile
from effect_store import mark_started, reconcile_started, record_no_trade, seal
from reporter import deliver, deliver_failure


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


def _publish_public_snapshot() -> bool:
    """Best-effort evidence sync; never authorize a retry of the trading pass."""
    publisher = Path(__file__).resolve().parents[2] / "apps/life-manager/scripts/publish-alpaca-public.js"
    try:
        completed = subprocess.run(
            ["node", str(publisher)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
        )
        return completed.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _retry_allowed(stage: str, effect_attempted: bool, attempt: int) -> bool:
    return stage != "telegram_deliver" and not effect_attempted and attempt < 2


def _terminal_effect(effect_attempted: bool) -> str:
    return "unknown" if effect_attempted else "none"


def main(*, attempt: int = 0, wake_id=None) -> int:
    wake_id = wake_id or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    state = Path(os.environ.get(
        "ALPACA_INVESTMENT_STATE_DIR",
        "~/.local/state/life-manager/alpaca-investment",
    )).expanduser()
    effect_attempted = False
    observation = None
    campaign = None
    stage = "start"
    try:
        credentials_path = Path(os.environ.get(
            "ANICCA_CREDENTIALS_FILE",
            "~/.local/share/anicca/credentials.json",
        )).expanduser()
        cli_path = Path(os.environ.get("ALPACA_CLI", "~/.local/bin/alpaca")).expanduser()
        stage = "reconcile_started"
        reconciliation = reconcile_started(
            state / "receipts.jsonl",
            lambda client_order_id: find_order_by_client_id(
                credentials_path=credentials_path,
                cli_path=cli_path,
                client_order_id=client_order_id,
            ),
        )
        stage = "observe"
        observation = observe(
            credentials_path=credentials_path,
            cli_path=cli_path,
        )
        stage = "campaign_read"
        campaign = reconcile(read_campaign_snapshot(
            credentials_path=credentials_path,
            cli_path=cli_path,
            symbols=SYMBOLS,
        ))
        effect = "none"
        if campaign["exit_status"] == "EXIT_READY":
            exit_decision = {
                "candidate_ref": CANDIDATE_REF,
                "gate": "campaign_exit_ready",
                "paper": True,
                "reason": "sealed_campaign_regular_session_positive_credit",
            }
            exit_order_path = state / "campaign-exit-order.json"
            if exit_order_path.is_file():
                stage = "campaign_exit_order_read"
                order = json.loads(exit_order_path.read_text(encoding="utf-8"))
            else:
                stage = "campaign_exit_order_build"
                order = exit_order(campaign)
                _atomic_json(exit_order_path, order)
            stage = "campaign_exit_submit"
            sealed = seal(state / "receipts.jsonl", exit_decision, order)
            mark_started(state / "receipts.jsonl", sealed)
            effect_attempted = True
            submit_order(credentials_path=credentials_path, cli_path=cli_path,
                         client_order_id=sealed["client_order_id"], order=order)
            stage = "campaign_exit_reconcile"
            reconcile_started(
                state / "receipts.jsonl",
                lambda value: find_order_by_client_id(
                    credentials_path=credentials_path, cli_path=cli_path, client_order_id=value),
            )
            effect = sealed["effect_id"]
            stage = "campaign_exit_observe"
            observation = observe(credentials_path=credentials_path, cli_path=cli_path)
            stage = "campaign_exit_campaign_read"
            campaign = reconcile(read_campaign_snapshot(
                credentials_path=credentials_path, cli_path=cli_path, symbols=SYMBOLS))
        stage = "allocator_read"
        allocator_snapshot = read_allocator_snapshot(
            credentials_path=credentials_path, cli_path=cli_path)
        candidates = build_candidates(allocator_snapshot)
        stage = "allocation_decide"
        decision = choose(
            allocator_snapshot, candidates, state,
            Path(__file__).resolve().parents[2] / "runtime/agent-runner/agent_runner.py",
            Path(__file__).resolve().parents[2],
        )
        if effect != "none" and decision["approved"]:
            decision["approved"] = False
            decision["gate"] = "campaign_exit_used_effect_limit"
        if decision["approved"]:
            stage = "allocation_order_build"
            order = order_for(decision)
            stage = "allocation_submit"
            sealed = seal(state / "receipts.jsonl", decision, order)
            mark_started(state / "receipts.jsonl", sealed)
            effect_attempted = True
            submit_order(credentials_path=credentials_path, cli_path=cli_path,
                         client_order_id=sealed["client_order_id"], order=order)
            stage = "allocation_reconcile"
            reconcile_started(
                state / "receipts.jsonl",
                lambda value: find_order_by_client_id(
                    credentials_path=credentials_path, cli_path=cli_path, client_order_id=value),
            )
            effect = sealed["effect_id"]
        else:
            record_no_trade(state / "receipts.jsonl", decision)
        stage = "state_write"
        _atomic_json(state / "allocation-latest.json", decision)
        _atomic_json(state / "observation-latest.json", observation)
        _atomic_json(state / "campaign.json", campaign)
        stage = "telegram_deliver"
        telegram = deliver(state, observation, campaign, decision, effect)
        snapshot_published = _publish_public_snapshot()
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
            "telegram_message_id": telegram["message_id"],
            "public_snapshot_published": snapshot_published,
        }
        print(json.dumps(summary, separators=(",", ":")))
        return 0
    except Exception:
        # Read/agent/report failures before an effect are transient-safe to retry. Once submit_order
        # was called, never retry: an unknown broker acknowledgement must reconcile on the next wake.
        if _retry_allowed(stage, effect_attempted, attempt):
            return main(attempt=attempt + 1, wake_id=wake_id)
        telegram = {"status": "delivery_uncertain"}
        failure_delivery_succeeded = False
        if stage != "telegram_deliver":
            try:
                telegram = deliver_failure(
                    state,
                    stage=stage,
                    effect_uncertain=effect_attempted or stage == "reconcile_started",
                    wake_id=wake_id,
                    observation=observation,
                    campaign=campaign,
                )
                failure_delivery_succeeded = True
            except Exception:
                pass
        if failure_delivery_succeeded:
            try:
                _publish_public_snapshot()
            except Exception:
                pass
        print(json.dumps({
            "blocker": "alpaca_pass_failed",
            "effect": _terminal_effect(effect_attempted),
            "loop_id": "alpaca-investment",
            "stage": stage,
            "status": "blocked",
            "telegram_status": telegram["status"],
        }, separators=(",", ":")))
        return 78


if __name__ == "__main__":
    raise SystemExit(main())
