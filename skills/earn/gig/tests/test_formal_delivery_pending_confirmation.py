from __future__ import annotations

import argparse
import asyncio
import importlib.util
import sys
from pathlib import Path

import pytest


# Talkroom 90000002 (project 91000002, buyer 買い手B): every formal-delivery attempt from
# 2026-08-06 onward died at formal_checkbox_readback_failed -- the checkbox was clicked but
# never read back as checked. Not a click bug, not a selector bug: the click and the
# readback share the exact same live-queried selector. formal-delivery-evidence.json already
# has a SUCCESSFUL formal_checkbox send on this same talkroom on 2026-08-06
# (formal_delivery_control_checked_before_send=true), which left the room in 納品確認待ち --
# awaiting the buyer's confirmation of THAT delivery. Coconala will not let a second formal
# delivery be checked while one is still pending, so the false readback was the site telling
# the truth: the loop spent six attempts arguing with the marketplace's own state machine.
#
# transaction_state is not a second DOM round trip -- state_expression() (used by both the
# click and the readback) already computes it from the step-bar text on the very first
# _wait_for_state read of the room (the `initial` state in execute()), so the fix costs
# nothing extra to observe.

MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "coconala_formal_delivery_browser.py"
)


def load_module():
    scripts_dir = str(MODULE_PATH.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("formal_delivery_pending", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


URL = "https://coconala.com/talkrooms/90000002"


def state(**overrides):
    base = {
        "url": URL,
        "transaction_state": "納品確認待ち",
        "form_present": True,
        "textarea_present": True,
        "formal_delivery_control_present": True,
        "formal_delivery_control_checked": False,
        "form_has_artifact": False,
        "send_button_present": True,
        "send_button_disabled": False,
        "subscription_room": False,
        "seller_messages": [],
    }
    base.update(overrides)
    return base


def test_pending_confirmation_blocks_a_fresh_formal_checkbox_room() -> None:
    m = load_module()
    assert m.formal_delivery_blocked_on_pending_confirmation("formal_checkbox", state()) is True


def test_an_in_progress_room_is_not_blocked() -> None:
    m = load_module()
    assert m.formal_delivery_blocked_on_pending_confirmation(
        "formal_checkbox", state(transaction_state="取引中")
    ) is False


def test_a_subscription_room_is_never_blocked_by_this_check() -> None:
    # 定期購入 rooms have no formal checkbox at all; this precondition only exists for the
    # room type it names, same scoping as the sibling formal_checkbox_not_initially_off guard.
    m = load_module()
    assert m.formal_delivery_blocked_on_pending_confirmation(
        "subscription_message", state()
    ) is False


# Order 91000002 (talkroom 90000002) measured 2026-08-08: the buyer never confirmed the first
# formal delivery -- they replied with a revision request (5 attached photos) while
# transaction_state stayed 納品確認待ち. This guard could not tell that apart from silence and
# blocked eight straight attempts against the SAME open request. revision_after_formal is the
# freshness signal gig_pass.sh already derives (feedback_sha256 != handled_buyer_feedback_sha256)
# and is what must lift the block -- without it, the guard's fail-closed default holds.


def test_revision_after_formal_lifts_the_block() -> None:
    m = load_module()
    assert m.formal_delivery_blocked_on_pending_confirmation(
        "formal_checkbox", state(), revision_after_formal=True
    ) is False


def test_without_revision_after_formal_the_block_still_holds() -> None:
    m = load_module()
    assert m.formal_delivery_blocked_on_pending_confirmation(
        "formal_checkbox", state(), revision_after_formal=False
    ) is True


def test_revision_after_formal_does_not_touch_the_subscription_room_scoping() -> None:
    # Already False for a subscription room either way; documents that the new kwarg cannot
    # flip a case this guard was never scoped to cover.
    m = load_module()
    assert m.formal_delivery_blocked_on_pending_confirmation(
        "subscription_message", state(), revision_after_formal=True
    ) is False


class FakeConnection:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, *args):
        return None


def test_execute_refuses_before_touching_the_checkbox_when_a_prior_delivery_is_pending(
    monkeypatch,
) -> None:
    m = load_module()
    contract = {
        "talkroom_url": URL,
        "artifact": Path("/tmp/deliverable-v6.zip"),
        "message": "第6版をお届けします。\n\n添付: deliverable-v6.zip",
    }
    args = argparse.Namespace(
        page_timeout=1, upload_timeout=1, send_timeout=1, post_timeout=1
    )

    async def fake_wait_for_state(session, expression, predicate, timeout, error, diagnose=None):
        return state()

    async def fake_session_call(self, method, params=None):
        return {}

    async def upload_must_not_be_called(session, artifact_path):
        raise AssertionError("upload attempted while a prior delivery awaits buyer confirmation")

    monkeypatch.setattr(m.websockets, "connect", lambda *a, **k: FakeConnection())
    monkeypatch.setattr(m.progress.CdpSession, "call", fake_session_call)
    monkeypatch.setattr(m.progress, "_wait_for_state", fake_wait_for_state)
    monkeypatch.setattr(m.progress, "_upload", upload_must_not_be_called)

    with pytest.raises(RuntimeError) as excinfo:
        asyncio.run(m.execute("ws://example.test/page", contract, args))
    assert "awaiting_buyer_confirmation" in str(excinfo.value)


class _ProceededPastGuard(Exception):
    """Marker: execute() reached the upload step instead of raising the guard."""


def test_execute_reaches_upload_when_the_contract_carries_revision_after_formal(
    monkeypatch,
) -> None:
    m = load_module()
    contract = {
        "talkroom_url": URL,
        "artifact": Path("/tmp/deliverable-v7.zip"),
        "message": "第7版をお届けします。\n\n添付: deliverable-v7.zip",
        "revision_after_formal": True,
    }
    args = argparse.Namespace(
        page_timeout=1, upload_timeout=1, send_timeout=1, post_timeout=1
    )

    async def fake_wait_for_state(session, expression, predicate, timeout, error, diagnose=None):
        return state()

    async def fake_session_call(self, method, params=None):
        return {}

    async def upload_reached(session, artifact_path):
        raise _ProceededPastGuard("upload reached: a fresh revision was not blocked")

    monkeypatch.setattr(m.websockets, "connect", lambda *a, **k: FakeConnection())
    monkeypatch.setattr(m.progress.CdpSession, "call", fake_session_call)
    monkeypatch.setattr(m.progress, "_wait_for_state", fake_wait_for_state)
    monkeypatch.setattr(m.progress, "_upload", upload_reached)

    with pytest.raises(_ProceededPastGuard):
        asyncio.run(m.execute("ws://example.test/page", contract, args))


# ★ The live DOM outranks the flag (Opus review 2026-08-08). ★ During 納品確認待ち the real
# room's checkbox is measured DISABLED (90000002: disabled=True on every snapshot since
# 16:30). Proceeding would upload + type + fail on the unclickable box -- the slow per-pass
# failure with compose residue that the review rejected. disabled=True must refuse before
# upload no matter what the contract says.


def test_a_disabled_live_checkbox_blocks_even_a_fresh_revision() -> None:
    m = load_module()
    assert m.formal_delivery_blocked_on_pending_confirmation(
        "formal_checkbox",
        state(formal_delivery_control_disabled=True),
        revision_after_formal=True,
    ) is True


def test_execute_refuses_before_upload_when_the_live_checkbox_is_disabled(
    monkeypatch,
) -> None:
    m = load_module()
    contract = {
        "talkroom_url": URL,
        "artifact": Path("/tmp/deliverable-v7.zip"),
        "message": "第7版をお届けします。\n\n添付: deliverable-v7.zip",
        "revision_after_formal": True,
    }
    args = argparse.Namespace(
        page_timeout=1, upload_timeout=1, send_timeout=1, post_timeout=1
    )

    async def fake_wait_for_state(session, expression, predicate, timeout, error, diagnose=None):
        return state(formal_delivery_control_disabled=True)

    async def fake_session_call(self, method, params=None):
        return {}

    async def upload_must_not_be_called(session, artifact_path):
        raise AssertionError("upload attempted against a disabled formal checkbox")

    monkeypatch.setattr(m.websockets, "connect", lambda *a, **k: FakeConnection())
    monkeypatch.setattr(m.progress.CdpSession, "call", fake_session_call)
    monkeypatch.setattr(m.progress, "_wait_for_state", fake_wait_for_state)
    monkeypatch.setattr(m.progress, "_upload", upload_must_not_be_called)

    with pytest.raises(RuntimeError) as excinfo:
        asyncio.run(m.execute("ws://example.test/page", contract, args))
    assert "awaiting_buyer_confirmation" in str(excinfo.value)
