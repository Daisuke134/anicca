from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


PATH = Path(__file__).resolve().parents[1] / "scripts" / "coconala_paid_adapter.py"


def load():
    spec = importlib.util.spec_from_file_location("coconala_paid_adapter_test", PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def item(event: str = "a" * 64) -> dict:
    return {
        "talkroom_id": "18211957", "buyer_feedback_sha256": event,
        "talkroom_state": "取引中", "talkroom_observed_at": "2026-09-07T00:00:00Z",
        "buyer": "buyer", "title": "work", "buyer_feedback_message_identities": ["m1"],
    }


def test_maps_coconala_identity_and_cumulative_context() -> None:
    module = load()
    adapter = module.CoconalaPaidAdapter(
        account_id="seller-1", inventory_reader=lambda: [item()],
        refresh_reader=lambda row: dict(row),
        context_reader=lambda row: {"requirements": ["deliver"], "attachments": []},
        effect_runner=lambda intent: None,
        readback_reader=lambda intent: {"verified": False},
    )
    rows = adapter.observe_active()
    assert rows == [{
        "provider": "coconala", "account_id": "seller-1", "work_id": "18211957",
        "latest_event_id": "a" * 64, "provider_state": "取引中",
        "observed_at": "2026-09-07T00:00:00Z",
    }]
    assert adapter.context("18211957") == {"requirements": ["deliver"], "attachments": []}


def test_refresh_uses_official_targeted_reader() -> None:
    module = load()
    refreshed = item("b" * 64)
    adapter = module.CoconalaPaidAdapter(
        account_id="seller-1", inventory_reader=lambda: [item()],
        refresh_reader=lambda row: refreshed,
        context_reader=lambda row: {}, effect_runner=lambda intent: None,
        readback_reader=lambda intent: {"verified": False},
    )
    adapter.observe_active()
    assert adapter.observe_one("18211957")["latest_event_id"] == "b" * 64


def test_mutation_and_readback_remain_adapter_owned() -> None:
    module = load()
    effects = []
    adapter = module.CoconalaPaidAdapter(
        account_id="seller-1", inventory_reader=lambda: [item()],
        refresh_reader=lambda row: row, context_reader=lambda row: {},
        effect_runner=lambda intent: effects.append(intent),
        readback_reader=lambda intent: {"verified": True, "provider_receipt_id": "message-9",
                                        "observed_at": "2026-09-07T00:01:00Z"},
    )
    intent = {"effect_key": "key", "work_id": "18211957"}
    adapter.mutate(intent)
    assert effects == [intent]
    assert adapter.readback(intent)["provider_receipt_id"] == "message-9"
