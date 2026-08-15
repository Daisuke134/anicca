from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


# The paying buyer of talkroom 90000004 (ウェブ画像の更新と軽微な調整, ¥2,500) purchased a
# SUBSCRIPTION (定期購入): the room's own screenshot shows the 定期購入 badge, "定期購入の
# 1回目の取引が開始されました", close date 8/30, and a 定期購入を終了する control. That room
# type has no 正式な納品 checkbox and no 納品確認待ち step -- the deliverable goes out as an
# attached message and the cycle completes on the close date.
#
# The delivery browser modelled only the one-shot room: readiness demanded a step-bar state
# this room never shows (measured: transaction_state="unknown",
# formal_delivery_control_present=false, form_present=true, textarea_present=true), so every
# attempt since 2026-08-03 died in _wait_for_state and the buyer had received nothing six
# days after paying.

MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "coconala_formal_delivery_browser.py"
)


def load_module():
    scripts_dir = str(MODULE_PATH.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("formal_delivery_sub", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


URL = "https://coconala.com/talkrooms/90000004"

# What the buyer now reads -- no sha256, so the text has to carry the identity itself.
DELIVERED_MESSAGE = (
    "お世話になっております。\n"
    "ご依頼いただいた件が仕上がりましたので、お届けいたします。\n"
    "今回対応したのは「トップページの画像を差し替え」です。\n"
    "\n"
    "添付のファイルをご確認ください。気になるところや直したい箇所がありましたら、"
    "このトークルームにそのままお書きいただければ、すぐに手を入れます。\n"
    "\n"
    "添付: deliverable.zip"
)


def subscription_state(**overrides):
    # The exact shape measured on 2026-08-06 05:01.
    state = {
        "url": URL,
        "transaction_state": "unknown",
        "form_present": True,
        "textarea_present": True,
        "formal_delivery_control_present": False,
        "formal_delivery_control_checked": False,
        "form_has_artifact": False,
        "send_button_present": True,
        "send_button_disabled": True,
        "subscription_room": True,
        "seller_messages": [],
    }
    state.update(overrides)
    return state


def test_the_measured_subscription_room_is_ready_for_delivery() -> None:
    m = load_module()
    assert m.talkroom_ready(subscription_state(), URL) is True


def test_a_one_shot_room_still_requires_its_step_state() -> None:
    m = load_module()
    state = subscription_state(subscription_room=False)
    assert m.talkroom_ready(state, URL) is False
    assert m.talkroom_ready(subscription_state(subscription_room=False, transaction_state="取引中"), URL) is True


def test_the_wrong_room_is_never_ready() -> None:
    m = load_module()
    state = subscription_state(url="https://coconala.com/talkrooms/999")
    assert m.talkroom_ready(state, URL) is False


def test_delivery_mode_names_the_room_type() -> None:
    m = load_module()
    assert m.delivery_mode(subscription_state()) == "subscription_message"
    assert m.delivery_mode(subscription_state(
        subscription_room=False, transaction_state="取引中",
        formal_delivery_control_present=True,
    )) == "formal_checkbox"


def test_subscription_delivery_verifies_by_the_visible_message_not_the_step_bar() -> None:
    # matching_delivery() is the site-side proof: our message, with the artifact attached and
    # our own opening text, visible in the room. A subscription room never reaches
    # 納品確認待ち, so demanding it would fail every successful delivery.
    #
    # The key was the sha256 printed at the end of the message until 2026-08-07. The sha is
    # gone from what the buyer reads, so the proof is now the text itself.
    m = load_module()
    contract = {
        "artifact": Path("/tmp/deliverable.zip"),
        "artifact_sha256": "a" * 64,
        "message": DELIVERED_MESSAGE,
    }
    delivered = subscription_state(seller_messages=[{
        "side": "seller",
        # As the DOM gives it back: reflowed whitespace, and truncated at the end.
        "text": DELIVERED_MESSAGE.replace("\n", "  \n ")[:120],
        "attachments": ["deliverable.zip"],
    }])
    assert m.post_send_verified(delivered, contract) is True
    assert m.post_send_verified(subscription_state(), contract) is False


def load_gate():
    path = Path(__file__).resolve().parents[1] / "scripts" / "paid_queue_evidence.py"
    scripts_dir = str(path.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("paid_queue_evidence_sub", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def gate_fixture(tmp_path: Path, *, delivery_mode: str, transaction_state: str,
                 checked_before_send: bool):
    import json as json_module
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "shot.png").write_bytes(b"png")
    live = {
        "url": URL,
        "sent": True,
        "mode": "formal",
        "send_performed": True,
        "deduplicated": False,
        "transaction_state": transaction_state,
        "delivery_mode": delivery_mode,
        "formal_delivery_control_checked": False,
        "formal_delivery_control_checked_before_send": checked_before_send,
        "latest_seller_attachment": {
            "filename": "a.zip",
            "size_bytes": 3,
            # As a delivered message now reads: no sha, because we no longer send one.
            "message": "修正版 v12 をお届けします。ご確認ください。\n添付: a.zip",
        },
    }
    (evidence / "dom.json").write_text(json_module.dumps(live), encoding="utf-8")
    manifest = {
        "sent": True,
        "mode": "formal",
        "formal_delivery_checkbox": True,
        "captured_at": "2026-08-06T05:58:00+00:00",
        "artifact_version": "v12",
        "package_sha256": "a" * 64,
        "acceptance_delta": ["直した"],
        "expected_url": URL,
        "screenshot_path": str(evidence / "shot.png"),
        "live_dom_path": str(evidence / "dom.json"),
    }
    (evidence / "paid-queue-evidence.json").write_text(
        json_module.dumps(manifest), encoding="utf-8"
    )
    return evidence


def test_the_gate_accepts_a_verified_subscription_delivery(tmp_path) -> None:
    # The exact rejection measured at 2026-08-06 05:58: the browser delivered (send readback,
    # attachment, sha in text), and validate_paid_queue still demanded the one-shot room's
    # 納品確認待ち step and checkbox readback -- states a 定期購入 room does not have. The
    # delivery succeeded on the site and the pass still reported failure.
    gate = load_gate()
    evidence = gate_fixture(
        tmp_path, delivery_mode="subscription_message",
        transaction_state="unknown", checked_before_send=False,
    )
    ok, errors = gate.validate_paid_queue(
        evidence, {"delivery_action": "formal", "marketplace_url": URL}
    )
    assert errors == []
    assert ok is True


def test_the_gate_accepts_a_delivery_whose_message_has_no_internal_tokens(tmp_path) -> None:
    # The gate required the artifact version AND the package sha256 to appear in the text
    # the buyer reads. Removing them from the message (2026-08-07) would otherwise have
    # failed every real delivery with latest_seller_message_hash_missing.
    gate = load_gate()
    evidence = gate_fixture(
        tmp_path, delivery_mode="subscription_message",
        transaction_state="unknown", checked_before_send=False,
    )
    ok, errors = gate.validate_paid_queue(
        evidence, {"delivery_action": "formal", "marketplace_url": URL}
    )
    assert errors == []
    assert ok is True


def test_the_gate_still_refuses_a_delivery_with_no_readback_at_all(tmp_path) -> None:
    # An empty readback means nothing was ever observed in front of the buyer.
    import json as json_module
    gate = load_gate()
    evidence = gate_fixture(
        tmp_path, delivery_mode="subscription_message",
        transaction_state="unknown", checked_before_send=False,
    )
    dom_path = evidence / "dom.json"
    live = json_module.loads(dom_path.read_text(encoding="utf-8"))
    live["latest_seller_attachment"]["message"] = "   "
    dom_path.write_text(json_module.dumps(live), encoding="utf-8")

    ok, errors = gate.validate_paid_queue(
        evidence, {"delivery_action": "formal", "marketplace_url": URL}
    )
    assert ok is False
    assert "latest_seller_message_missing" in errors


def test_the_gate_still_requires_the_step_for_one_shot_rooms(tmp_path) -> None:
    gate = load_gate()
    evidence = gate_fixture(
        tmp_path, delivery_mode="formal_checkbox",
        transaction_state="unknown", checked_before_send=True,
    )
    ok, errors = gate.validate_paid_queue(
        evidence, {"delivery_action": "formal", "marketplace_url": URL}
    )
    assert ok is False
    assert "formal_delivery_transaction_state_missing" in errors


def test_one_shot_delivery_still_requires_the_acceptance_step() -> None:
    m = load_module()
    contract = {
        "artifact": Path("/tmp/deliverable.zip"),
        "artifact_sha256": "a" * 64,
        "message": DELIVERED_MESSAGE,
    }
    message = {
        "side": "seller",
        "text": DELIVERED_MESSAGE,
        "attachments": ["deliverable.zip"],
    }
    visible_but_not_accepted = subscription_state(
        subscription_room=False, transaction_state="取引中", seller_messages=[message]
    )
    assert m.post_send_verified(visible_but_not_accepted, contract) is False
    accepted = subscription_state(
        subscription_room=False, transaction_state="納品確認待ち", seller_messages=[message]
    )
    assert m.post_send_verified(accepted, contract) is True
