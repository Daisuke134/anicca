from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "capafy_company_receipt.py"
GOAL_MONITOR = Path(__file__).parents[1] / "capafy-goal-monitor.sh"


def load_module():
    spec = importlib.util.spec_from_file_location("capafy_company_receipt", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sources() -> dict:
    return {
        "inventory": {
            "readable": True,
            "counts": {"total": 32, "listed": 22, "occupied": 3, "free": 2, "retry": 7, "blocked": 0, "unknown": 0},
        },
        "candidate": {
            "candidate_id": "capafy-o13-interviews",
            "title": "Interview Synthesizer",
            "content_sha256": "sha256:" + "a" * 64,
            "state": "ready",
            "platform_state": "not_submitted",
        },
        "marketing": {
            "telegram_message_id": "27263",
            "outcome": {
                "agent_id": "7785270416",
                "title": "Data Analyst",
                "reel_url": "https://www.instagram.com/reel/abc/",
                "media_sha256": "sha256:" + "b" * 64,
                "owner_session_verified": True,
            },
        },
        "money": {
            "observed_at": "2026-08-22T10:00:00Z",
            "orders": 5,
            "money": {"gross_usd": "19.98", "one_time_revenue_usd": None, "pending_usd": "8.00", "realized_usd": "0.00", "refunds_usd": "0.00", "settled_mrr_usd": None, "net_mrr_usd": None},
            "money_status": {"settled_mrr_usd": "unknown_no_seller_subscription_source"},
        },
    }


def test_receipt_joins_skill_slots_post_money_under_one_run_id() -> None:
    module = load_module()
    receipt = module.build_receipt(sources(), "2026-08-22T11:00:00Z")

    assert receipt["run_id"].startswith("capafy-")
    assert receipt["skill"]["candidate_id"] == "capafy-o13-interviews"
    assert receipt["slots"]["occupied"] == 3
    assert receipt["distribution"][0]["native_url"].endswith("/abc/")
    assert receipt["money"]["gross_usd"] == "19.98"
    assert receipt["money"]["settled_mrr_usd"] is None
    assert receipt["telegram"] == {"status": "pending", "message_id": None}


def test_semantic_replay_has_same_run_id_but_new_state_changes_it() -> None:
    module = load_module()
    first = module.build_receipt(sources(), "2026-08-22T11:00:00Z")
    replay = module.build_receipt(sources(), "2026-08-22T12:00:00Z")
    changed_sources = sources()
    changed_sources["inventory"]["counts"]["occupied"] = 4
    changed = module.build_receipt(changed_sources, "2026-08-22T12:00:00Z")

    assert first["run_id"] == replay["run_id"]
    assert changed["run_id"] != first["run_id"]


def test_delivery_sends_exact_state_once_and_persists_message_id(tmp_path: Path) -> None:
    module = load_module()
    calls = []

    def sender(message: str) -> str:
        calls.append(message)
        return "9001"

    receipt = module.build_receipt(sources(), "2026-08-22T11:00:00Z")
    first = module.deliver_receipt(receipt, tmp_path / "outbox.sqlite", tmp_path / "receipts", sender)
    replay = module.deliver_receipt(receipt, tmp_path / "outbox.sqlite", tmp_path / "receipts", sender)

    assert calls == [module.render_message(receipt)]
    assert first["telegram"] == {"status": "delivered", "message_id": "9001"}
    assert replay == first
    persisted = json.loads((tmp_path / "receipts" / f"{receipt['run_id']}.json").read_text())
    assert persisted["telegram"]["message_id"] == "9001"


def test_provider_without_message_id_is_quarantined_and_not_retried(tmp_path: Path) -> None:
    module = load_module()
    calls = 0

    def sender(_message: str) -> str:
        nonlocal calls
        calls += 1
        raise module.DeliveryUncertain("message_id_missing")

    receipt = module.build_receipt(sources(), "2026-08-22T11:00:00Z")
    first = module.deliver_receipt(receipt, tmp_path / "outbox.sqlite", tmp_path / "receipts", sender)
    replay = module.deliver_receipt(receipt, tmp_path / "outbox.sqlite", tmp_path / "receipts", sender)

    assert calls == 1
    assert first["telegram"]["status"] == "delivery_uncertain"
    assert replay == first


def test_hourly_goal_monitor_uses_unified_receipt_before_legacy_sender() -> None:
    source = GOAL_MONITOR.read_text()
    hourly = source.index('CAPAFY_REPORT_KIND:-morning')
    reconcile = source.index("capafy_hourly_reconcile.py", hourly)
    receipt = source.index("capafy_company_receipt.py", reconcile)
    legacy = source.index("openclaw message send", receipt)

    assert hourly < reconcile < receipt < legacy
    assert 'if [ "$REPORT_KIND" = "hourly" ]' in source
    assert 'exit "$UNIFIED_RC"' in source
