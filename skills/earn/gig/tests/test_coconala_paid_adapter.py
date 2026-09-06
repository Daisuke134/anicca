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


def test_shared_decision_preserves_coconala_effect_kind() -> None:
    module = load()
    base = {"context": {"_paid_prepare_status": "prepared",
                        "_bridge_prepared_path": "/tmp/prepared.json"}}
    assert module._decision({**base, "context": {**base["context"],
                              "_paid_mode": "cancellation"}})["action"] == "cancel"
    assert module._decision({**base, "context": {**base["context"],
                              "_paid_mode": "file", "delivery_action": "progress"}})["action"] == "submit"
    formal = {**base, "context": {**base["context"],
                                   "_paid_mode": "file", "delivery_action": "formal"}}
    assert module._decision(formal) == {
        "action": "wait", "reason": "formal_delivery_disabled",
        "remaining_work": ["retain prepared delivery until formal delivery is authorized"],
    }
    assert module._decision(formal, allow_formal_delivery=True)["action"] == "formal_delivery"
    assert module._decision({**base, "context": {**base["context"],
                              "_paid_mode": "answer"}})["action"] == "answer"


def test_shared_decision_maps_existing_terminal_and_wait_states() -> None:
    module = load()
    assert module._decision({"context": {"_paid_prepare_status": "no_effect"}}) == {
        "action": "noop"
    }
    assert module._decision({"context": {
        "_paid_prepare_status": "pending", "reason": "external_access",
        "remaining_work": ["obtain access"],
    }}) == {"action": "wait", "reason": "external_access",
           "remaining_work": ["obtain access"]}


def test_default_build_reuses_paid_direct_runtime_without_copying_owner(tmp_path: Path) -> None:
    module = load()
    adapter, decide = module.build([
        "--account-id", "seller-1",
        "--bridge-root", str(tmp_path / "bridge"),
        "--evidence-dir", str(tmp_path / "evidence"),
        "--projects-root", str(tmp_path / "projects"),
    ])
    assert isinstance(adapter, module.CoconalaPaidAdapter)
    assert adapter.account_id == "seller-1"
    assert decide({"context": {"_paid_prepare_status": "no_effect"}}) == {"action": "noop"}
    assert adapter.context_reader.__self__.paid.__file__.endswith("/paid_direct.py")
