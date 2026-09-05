from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load():
    path = SCRIPTS / "coconala_cancel_browser.py"
    spec = importlib.util.spec_from_file_location("coconala_cancel_browser_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_module(name: str):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"{name}_cancel_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def contract(cancel):
    queue = {
        "talkroom_id": "18218780",
        "marketplace_url": "https://coconala.com/talkrooms/18218780",
        "buyer_feedback_sha256": "a" * 64,
        "buyer_feedback_message_identities": ["message:m1", "message:m2"],
    }
    requirements = {
        "talkroom_id": "18218780",
        "feedback_sha256": "a" * 64,
        "feedback_message_identities": ["message:m1", "message:m2"],
        "feedback_text": "キャンセルの手続きをお願いします。\nありがとうございます。",
    }
    return cancel.validate_contract(queue, requirements)


def live_state(cancel, *, formal=False, ids=("m1", "m2"), existing=False):
    c = contract(cancel)
    return {
        "url": c.talkroom_url,
        "transaction_state": "取引中",
        "formal_delivery_control_checked": formal,
        "cancel_control_present": not existing,
        "buyer_messages": [
            {"message_id": value, "text": text}
            for value, text in zip(ids, ("キャンセルの手続きをお願いします。", "ありがとうございます。"))
        ],
        "cancellation_pending": existing,
        "cancellation_reason_observed": c.reason if existing else "",
        "cancellation_detail_observed": c.detail if existing else "",
    }


def test_contract_binds_exact_feedback_and_reason():
    cancel = load()

    value = contract(cancel)

    assert value.reason == "出品者の都合で提供できなくなった"
    assert value.feedback_sha256 == "a" * 64
    assert "購入者様のご希望に沿って" in value.detail


@pytest.mark.parametrize("change", ["formal", "stale"])
def test_presend_rejects_formal_or_stale_buyer_state(change):
    cancel = load()
    state = live_state(
        cancel,
        formal=change == "formal",
        ids=("old", "m2") if change == "stale" else ("m1", "m2"),
    )

    assert cancel.ready_to_send(state, contract(cancel)) is False


def test_matching_official_cancellation_is_deduplicated():
    cancel = load()
    value = contract(cancel)

    assert cancel.matching_cancellation(live_state(cancel, existing=True), value) is True


@pytest.mark.parametrize("change", ["closed", "control_returned"])
def test_old_or_rejected_cancellation_history_is_not_current(change):
    cancel = load()
    state = live_state(cancel, existing=True)
    if change == "closed":
        state["transaction_state"] = "クローズ"
    else:
        state["cancel_control_present"] = True

    assert cancel.matching_cancellation(state, contract(cancel)) is False


def test_cancel_send_button_is_scoped_to_visible_modal():
    cancel = load()
    expression = cancel.cancel_send_button_expression()

    assert "modal.querySelectorAll('button')" in expression
    assert "[...document.querySelectorAll('button')]" not in expression


def test_pending_readback_excludes_answered_history_and_requires_no_current_control():
    cancel = load()
    expression = cancel.browser_state_expression(cancel.REASON, cancel.DETAIL)

    assert "const pending=!cancel&&" in expression
    assert "への回答" not in expression


@pytest.mark.parametrize("phase", ["click_started", "verified"])
def test_started_or_verified_intent_can_only_reconcile(phase):
    cancel = load()

    assert cancel.intent_is_reconcile_only({"effect_key": "same", "phase": phase}, "same") is True
    assert cancel.intent_is_reconcile_only({"effect_key": "other", "phase": phase}, "same") is False


def test_contract_rejects_non_cancellation_feedback():
    cancel = load()
    queue = {
        "talkroom_id": "1",
        "marketplace_url": "https://coconala.com/talkrooms/1",
        "buyer_feedback_sha256": "b" * 64,
        "buyer_feedback_message_identities": ["message:m1"],
    }
    requirements = {
        "talkroom_id": "1",
        "feedback_sha256": "b" * 64,
        "feedback_message_identities": ["message:m1"],
        "feedback_text": "修正をお願いします。",
    }

    with pytest.raises(ValueError, match="buyer_cancellation_not_requested"):
        cancel.validate_contract(queue, requirements)


def test_paid_routes_only_exact_adapter_block_to_cancellation():
    paid = load_module("paid_direct")
    matching = {
        "decision": "blocked",
        "required_effect": "Submit the cancellation request through the Coconala transaction controls.",
        "unresolved": ["No code-owned Coconala cancellation adapter is present."],
    }

    assert paid._is_coconala_cancellation_block(matching) is True
    assert paid._is_coconala_cancellation_block({
        **matching, "required_effect": "Restore the customer website."
    }) is False


def test_paid_aggregation_preserves_cancellation_effect(tmp_path, monkeypatch):
    paid = load_module("paid_direct")
    prepared_path = tmp_path / "prepared.json"

    def run_prepare(*_args, **_kwargs):
        paid._write(prepared_path, {
            "status": "completed", "effect": 1, "readback": 1, "failed": 0,
            "_paid_prepare_status": "terminal_effect",
            "item": {
                "send_performed": True, "deduplicated": False,
                "formal_delivery_checkbox": False, "effect_key": "key",
                "evidence_paths": {"official_readback": "/evidence.json"},
            },
        })
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(paid, "_prepare_command", lambda *_args: ["prepare"])
    monkeypatch.setattr(paid, "_run_bounded", run_prepare)

    row, effect, readback, failed, step = paid._run_paid_item(
        SimpleNamespace(cdp_lock_dir=tmp_path), "18218780", tmp_path / "item.json",
        prepared_path, tmp_path / "effect.json",
    )

    assert (row["status"], row["send_performed"], effect, readback, failed, step) == (
        "completed", True, 1, 1, 0, "",
    )
