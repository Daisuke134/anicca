import importlib.util
import hashlib
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "delivery_cadence.py"
SPEC = importlib.util.spec_from_file_location("delivery_cadence", SCRIPT)
cadence = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cadence)


def test_progress_payload_is_buyer_visible_and_formal_checkbox_off():
    payload = cadence.progress_payload({
        "request_id": "req-42",
        "artifact_version": "v2",
        "artifact_path": "/tmp/artifact-v2.zip",
        "package_sha256": "a" * 64,
        "acceptance_status": "FAIL",
        "acceptance_delta": ["2/7 images pass"],
        "blockers": ["missing_acceptance_evidence"],
    })
    assert payload["mode"] == "progress"
    assert payload["formal_delivery_checkbox"] is False
    assert "v2" in payload["message"]
    # Internal blocker identifiers must NEVER reach buyer-facing text.
    assert "missing_acceptance_evidence" not in payload["message"]
    assert "_" not in payload["message"]
    assert "2/7 images pass" in payload["message"]
    assert payload["buyer_visible"] is True


def test_formal_is_allowed_only_after_artifact_acceptance_hash_and_agreement(tmp_path):
    acceptance = tmp_path / "acceptance.json"
    acceptance.write_text('{"status":"PASS"}\n', encoding="utf-8")
    artifact = tmp_path / "artifact-v1.zip"
    artifact.write_bytes(b"accepted artifact")
    base = {
        "request_id": "req-42",
        "artifact_version": "v1",
        "artifact_path": str(artifact),
        "package_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "acceptance_status": "PASS",
        "acceptance_evidence_path": str(acceptance),
        "buyer_agreement_observed": True,
    }
    assert cadence.delivery_decision(base)["mode"] == "formal"
    assert cadence.delivery_decision(dict(base, blockers=["formal_delivery_not_confirmed"]))["mode"] == "formal"
    # Buyer agreement is NOT a formal-delivery prerequisite (Dais ruling
    # 2026-07-25): submission happens as soon as the work gates pass.
    assert cadence.delivery_decision(dict(base, buyer_agreement_observed=False))["mode"] == "formal"
    # But an unprocessed buyer message after our artifact must be handled first.
    for flag in ("buyer_feedback_pending_artifact", "buyer_reply_after_artifact_observed"):
        blocked = cadence.delivery_decision(dict(base, **{flag: True}))
        assert blocked["mode"] == "progress"
        assert "buyer_feedback_unprocessed" in blocked["blockers"]
    assert cadence.delivery_decision(dict(base, acceptance_evidence=True, acceptance_evidence_path="/missing/acceptance.json"))["mode"] == "progress"
    for field, value in (("acceptance_status", "FAIL"), ("acceptance_evidence_path", "/missing/acceptance.json")):
        item = dict(base, **{field: value})
        assert cadence.delivery_decision(item)["mode"] == "progress"
        assert cadence.delivery_decision(item)["formal_delivery_checkbox"] is False


def test_post_submit_state_is_observed_as_no_action():
    decision = cadence.delivery_decision({
        "formal_delivery_observed": True,
        "talkroom_state": "納品確認待ち",
        "blockers": ["missing_acceptance_evidence"],
    })
    assert decision["mode"] == "none"
    assert decision["blockers"] == []


def test_buyer_reply_after_formal_submit_reopens_progress_delivery():
    decision = cadence.delivery_decision({
        "formal_delivery_observed": True,
        "talkroom_state": "納品確認待ち",
        "buyer_feedback_pending_artifact": True,
        "buyer_reply_after_artifact_observed": True,
        "blockers": ["missing_versioned_artifact", "missing_acceptance_evidence"],
    })
    assert decision["mode"] == "progress"
    assert "missing_versioned_artifact" in decision["blockers"]
    assert decision["formal_delivery_checkbox"] is False


def test_inquiry_queue_is_generic_and_requires_reply_when_buyer_is_last():
    rows = cadence.inquiries_from_dom({"cards": [
        {"talkroom_url": "https://coconala.com/talkrooms/42", "buyer": "buyer-a", "title": "相談", "last_message_side": "buyer", "unread": True},
        {"talkroom_url": "https://coconala.com/talkrooms/43", "buyer": "buyer-b", "title": "相談", "last_message_side": "seller", "unread": False},
    ]})
    assert rows[0]["talkroom_id"] == "42"
    assert rows[0]["reply_required"] is True
    assert rows[1]["reply_required"] is False
    assert "buyer-a" not in json.dumps(rows[0], ensure_ascii=False)  # no raw buyer identity in reply prompt payload


def test_inquiry_evidence_requires_real_screenshot_and_post_send_dom(tmp_path):
    screenshot = tmp_path / "reply.png"
    screenshot.write_bytes(b"png")
    live_dom = tmp_path / "live-dom.json"
    live_dom.write_text(json.dumps({"url": "https://coconala.com/talkrooms/42", "reply_sent": True}), encoding="utf-8")
    (tmp_path / "inquiry-actions.json").write_text(json.dumps([{
        "talkroom_id": "42",
        "url": "https://coconala.com/talkrooms/42",
        "sent": True,
        "screenshot_path": str(screenshot),
        "live_dom_path": str(live_dom),
    }]), encoding="utf-8")
    assert cadence.validate_inquiry_evidence(tmp_path, ["42"]) == (True, [])
    (tmp_path / "inquiry-actions.json").write_text(json.dumps([{
        "talkroom_id": "42", "url": "https://coconala.com/talkrooms/42", "sent": True,
        "screenshot_path": str(tmp_path / "missing.png"), "live_dom_path": str(tmp_path / "bad-live-dom.json"),
    }]), encoding="utf-8")
    ok, errors = cadence.validate_inquiry_evidence(tmp_path, ["42"])
    assert not ok
    assert "missing_inquiry_screenshot:42" in errors
    assert "missing_post_send_live_dom:42" in errors
    outside = tmp_path.parent / "outside-reply.png"
    outside.write_bytes(b"png")
    (tmp_path / "inquiry-actions.json").write_text(json.dumps([{
        "talkroom_id": "42", "url": "https://coconala.com/talkrooms/42", "sent": True,
        "screenshot_path": str(outside), "live_dom_path": str(live_dom),
    }]), encoding="utf-8")
    ok, errors = cadence.validate_inquiry_evidence(tmp_path, ["42"])
    assert not ok and "missing_inquiry_screenshot:42" in errors
