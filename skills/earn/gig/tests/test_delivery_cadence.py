import importlib.util
import hashlib
import json
import os
import zipfile
from datetime import datetime, timezone
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


def test_recipient_access_contract_rejects_zip_but_allows_nonarchive(tmp_path):
    archive = tmp_path / "artifact-v1.zip"
    archive.write_bytes(b"zip-shaped artifact")
    html = tmp_path / "artifact-v1.html"
    html.write_text("<html><body>openable draft</body></html>\n", encoding="utf-8")
    renamed_archive = tmp_path / "artifact-v1.bin"
    with zipfile.ZipFile(renamed_archive, "w") as bundle:
        bundle.writestr("draft.txt", "still an archive")

    required = {"recipient_access_required": True, "artifact_version": "v1"}
    assert cadence._artifact_ready(dict(required, artifact_path=str(archive))) is False
    assert cadence._artifact_ready(dict(required, artifact_path=str(html))) is True
    assert cadence._artifact_ready(dict(required, artifact_path=str(renamed_archive))) is False
    assert cadence._artifact_ready({"artifact_version": "v1", "artifact_path": str(archive)}) is True


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
    # It is work, not a buyer-visible event: the artifact on disk does not yet
    # answer what the buyer just asked, so there is nothing honest to send.
    for flag in ("buyer_feedback_pending_artifact", "buyer_reply_after_artifact_observed"):
        blocked = cadence.delivery_decision(dict(base, **{flag: True}))
        assert blocked["mode"] == "work_required"
        assert blocked["buyer_visible"] is False
        assert "buyer_feedback_unprocessed" in blocked["blockers"]
    assert cadence.delivery_decision(dict(base, acceptance_evidence=True, acceptance_evidence_path="/missing/acceptance.json"))["mode"] == "progress"
    for field, value in (("acceptance_status", "FAIL"), ("acceptance_evidence_path", "/missing/acceptance.json")):
        item = dict(base, **{field: value})
        assert cadence.delivery_decision(item)["mode"] == "progress"
        assert cadence.delivery_decision(item)["formal_delivery_checkbox"] is False


def test_explicit_buyer_formal_delivery_hold_fails_closed_even_when_work_is_ready(tmp_path):
    acceptance = tmp_path / "acceptance.json"
    acceptance.write_text('{"status":"PASS"}\n', encoding="utf-8")
    artifact = tmp_path / "artifact-v1.zip"
    artifact.write_bytes(b"accepted artifact")
    decision = cadence.delivery_decision({
        "artifact_version": "v1",
        "artifact_path": str(artifact),
        "package_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "acceptance_status": "PASS",
        "acceptance_evidence_path": str(acceptance),
        "buyer_formal_delivery_hold": True,
        "buyer_formal_delivery_hold_reason": "buyer_explicit_formal_delivery_hold",
    })
    assert decision["mode"] == "work_required"
    assert decision["formal_delivery_checkbox"] is False
    assert decision["buyer_visible"] is False
    assert decision["blockers"] == ["buyer_explicit_formal_delivery_hold"]


def test_absent_or_false_buyer_formal_delivery_hold_preserves_legacy_formal_path(tmp_path):
    acceptance = tmp_path / "acceptance.json"
    acceptance.write_text('{"status":"PASS"}\n', encoding="utf-8")
    artifact = tmp_path / "artifact-v1.zip"
    artifact.write_bytes(b"accepted artifact")
    base = {
        "artifact_version": "v1",
        "artifact_path": str(artifact),
        "package_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "acceptance_status": "PASS",
        "acceptance_evidence_path": str(acceptance),
    }
    assert cadence.delivery_decision(base)["mode"] == "formal"
    assert cadence.delivery_decision(dict(base, buyer_formal_delivery_hold=False))["mode"] == "formal"


def test_buyer_hold_allows_nonformal_progress_after_new_artifact_answers_feedback(tmp_path):
    acceptance = tmp_path / "acceptance.json"
    acceptance.write_text('{"status":"PASS"}\n', encoding="utf-8")
    artifact = tmp_path / "saved-draft-v2.html"
    artifact.write_text("<html><body>draft</body></html>\n", encoding="utf-8")
    os.utime(artifact, (1, 1))
    feedback = "f" * 64
    requirements = tmp_path / "live-buyer-reply.json"
    requirements.write_text(json.dumps({
        "feedback_sha256": feedback,
        "feedback_first_observed_at": "2026-08-10T00:00:00+00:00",
    }), encoding="utf-8")
    decision = cadence.delivery_decision({
        "artifact_path": str(artifact),
        "artifact_version": "v2",
        "package_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "acceptance_status": "PASS",
        "acceptance_evidence_path": str(acceptance),
        "acceptance_delta": ["開ける形式の保存用下書きを用意しました。"],
        "buyer_formal_delivery_hold": True,
        "buyer_feedback_pending_artifact": True,
        "buyer_reply_after_artifact_observed": True,
        "buyer_feedback_sha256": feedback,
        "requirements_path": str(requirements),
    })
    assert decision["mode"] == "progress"
    assert decision["formal_delivery_checkbox"] is False
    assert decision["buyer_visible"] is True
    assert decision["blockers"] == [cadence.BUYER_FORMAL_DELIVERY_HOLD_BLOCKER]


def test_post_submit_state_is_observed_as_no_action(tmp_path):
    """A delivered order with no standing block is finished, and stays finished.

    The project root is required, not decorative: after 91000002 an order may only be
    closed out when we could actually look for the builder's BLOCKED record and did not
    find one. An item that cannot name its project has not been checked -- see
    test_stub_delivery_is_not_done.py.
    """
    project_root = tmp_path / "1000"
    (project_root / "evidence").mkdir(parents=True)
    decision = cadence.delivery_decision({
        "formal_delivery_observed": True,
        "talkroom_state": "納品確認待ち",
        "project_root": str(project_root),
        "blockers": ["missing_acceptance_evidence"],
    })
    assert decision["mode"] == "none"
    assert decision["blockers"] == []


def test_artifact_older_than_matching_feedback_remains_unprocessed(tmp_path):
    acceptance = tmp_path / "acceptance.json"
    acceptance.write_text('{"status":"PASS"}\n', encoding="utf-8")
    artifact = tmp_path / "artifact-v1.zip"
    artifact.write_bytes(b"accepted artifact")
    feedback_hash = "b" * 64
    requirements = tmp_path / "requirements.json"
    future = artifact.stat().st_mtime + 60
    requirements.write_text(json.dumps({
        "feedback_sha256": feedback_hash,
        "observed_at": datetime.fromtimestamp(future, timezone.utc).isoformat(),
    }) + "\n", encoding="utf-8")

    decision = cadence.delivery_decision({
        "artifact_version": "v1",
        "artifact_path": str(artifact),
        "package_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "acceptance_status": "PASS",
        "acceptance_evidence_path": str(acceptance),
        "buyer_feedback_pending_artifact": True,
        "buyer_feedback_sha256": feedback_hash,
        "requirements_path": str(requirements),
    })

    assert decision["mode"] == "work_required"
    assert "buyer_feedback_unprocessed" in decision["blockers"]


def test_buyer_reply_after_formal_submit_reopens_work_not_a_promise():
    """A buyer reply after 納品確認待ち reopens the transaction — as work.

    The old contract called this "reopens progress delivery", which meant the
    pass sent a buyer-visible message with no artifact behind it. Reopening is
    real, but what it reopens is the builder, not the talkroom.
    """
    decision = cadence.delivery_decision({
        "formal_delivery_observed": True,
        "talkroom_state": "納品確認待ち",
        "buyer_feedback_pending_artifact": True,
        "buyer_reply_after_artifact_observed": True,
        "blockers": ["missing_versioned_artifact", "missing_acceptance_evidence"],
    })
    assert decision["mode"] == "work_required"
    assert decision["buyer_visible"] is False
    assert "missing_versioned_artifact" in decision["blockers"]
    assert decision["formal_delivery_checkbox"] is False


def test_absent_artifact_is_work_required_even_with_no_open_buyer_message():
    """P0-1: silence from the buyer is not permission to promise.

    Without an artifact there is nothing to attach, so a "progress" message
    could only say that something will follow later. That state is work.
    """
    decision = cadence.delivery_decision({
        "artifact_version": "v3",
        "artifact_path": "/nonexistent/artifact-v3.zip",
        "blockers": ["missing_versioned_artifact", "missing_package_hash"],
    })
    assert decision["mode"] == "work_required"
    assert decision["buyer_visible"] is False
    assert decision["formal_delivery_checkbox"] is False


def test_progress_payload_never_promises_a_later_send(tmp_path):
    """An empty change list must not turn into contentless reassurance."""
    artifactless = cadence.progress_payload({
        "artifact_version": "v3",
        "artifact_path": str(tmp_path / "missing-v3.zip"),
        "acceptance_delta": [],
        "blockers": ["missing_versioned_artifact"],
    })
    assert artifactless["mode"] == "work_required"
    assert artifactless["buyer_visible"] is False
    assert artifactless["message"] == ""

    # A real artifact with no change bullets is still a real send.
    artifact = tmp_path / "artifact-v4.zip"
    artifact.write_bytes(b"real artifact")
    shipped = cadence.progress_payload({
        "artifact_version": "v4",
        "artifact_path": str(artifact),
        "acceptance_delta": [],
        "blockers": ["missing_acceptance_evidence"],
    })
    assert shipped["mode"] == "progress"
    assert shipped["buyer_visible"] is True
    assert "v4" in shipped["message"]
    for promise in ("まとまり次第", "お待ちください", "進めています"):
        assert promise not in shipped["message"], shipped["message"]


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


def _finished_order(tmp_path, *, open_buyer_decisions=None):
    """Every delivery gate passed and the buyer's current request is answered."""
    root = tmp_path / "projects" / "90000004"
    (root / "requirements").mkdir(parents=True)
    acceptance = root / "acceptance.json"
    acceptance.write_text('{"status":"PASS"}\n', encoding="utf-8")
    artifact = root / "artifact-v17.html"
    artifact.write_bytes(b"delivered artifact")
    requirements = root / "requirements" / "live-buyer-reply.json"
    feedback_hash = "c" * 64
    requirements.write_text(json.dumps({
        "feedback_sha256": feedback_hash,
        # Older than the artifact: the artifact answers this request.
        "observed_at": datetime.fromtimestamp(
            artifact.stat().st_mtime - 60, timezone.utc,
        ).isoformat(),
    }) + "\n", encoding="utf-8")
    state = {"work_state": "DELIVERED", "next_action": "await_buyer_decision"}
    if open_buyer_decisions is not None:
        state["open_buyer_decisions"] = open_buyer_decisions
    (root / "state.json").write_text(json.dumps(state), encoding="utf-8")
    return {
        "project_root": str(root),
        "artifact_version": "v17",
        "artifact_path": str(artifact),
        "package_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "acceptance_status": "PASS",
        "acceptance_evidence_path": str(acceptance),
        "buyer_feedback_pending_artifact": True,
        "buyer_feedback_sha256": feedback_hash,
        "requirements_path": str(requirements),
        "blockers": ["formal_delivery_not_confirmed"],
    }


def test_a_question_parked_on_the_buyer_is_not_our_backlog(tmp_path):
    """Order 90000004: the buyer's executive owes us a button size.

    Nothing we build answers that, and it must not read as unprocessed feedback
    (which routed the order to work_required every hour) nor as a reason to fire
    a formal delivery.
    """
    item = _finished_order(tmp_path, open_buyer_decisions=[
        {"item": "発注書ボタンのサイズ", "status": "awaiting_buyer_executive_decision"},
    ])
    decision = cadence.delivery_decision(item)
    assert decision["mode"] == "none"
    assert decision["awaiting_buyer_decision"] is True
    assert decision["formal_delivery_checkbox"] is False
    assert "buyer_feedback_unprocessed" not in decision["blockers"]


def test_without_a_parked_buyer_decision_a_finished_order_delivers_formally(tmp_path):
    decision = cadence.delivery_decision(_finished_order(tmp_path))
    assert decision["mode"] == "formal"
    assert decision.get("awaiting_buyer_decision") is None


def test_a_parked_buyer_decision_never_parks_an_order_that_still_owes_work(tmp_path):
    """We owe the buyer work: that outranks anything they owe us."""
    item = _finished_order(tmp_path, open_buyer_decisions=[
        {"item": "発注書ボタンのサイズ", "status": "awaiting_buyer_executive_decision"},
    ])
    # No digest at all is the shape that made buyer_feedback_unprocessed permanent.
    item.pop("buyer_feedback_sha256")
    decision = cadence.delivery_decision(item)
    assert decision["mode"] == "work_required"
    assert "buyer_feedback_unprocessed" in decision["blockers"]
    assert decision.get("awaiting_buyer_decision") is None


def test_a_resolved_buyer_decision_no_longer_parks_the_order(tmp_path):
    item = _finished_order(tmp_path, open_buyer_decisions=[
        {"item": "発注書ボタンのサイズ", "status": "buyer_answered"},
    ])
    assert cadence.delivery_decision(item)["mode"] == "formal"


def test_a_disabled_formal_checkbox_routes_a_fresh_revision_to_progress(tmp_path):
    """Order 91000002 (talkroom 90000002), Opus review 2026-08-08: during 納品確認待ち the
    live formal checkbox is DISABLED -- every snapshot since 16:30 carries
    formal_delivery_control_disabled=True. A formal mode there is physically impossible;
    the revision must ride the progress channel, whose browser skips the checkbox.
    """
    item = dict(
        _finished_order(tmp_path),
        formal_delivery_observed=True,
        talkroom_state="納品確認待ち",
        formal_delivery_control_disabled=True,
    )
    decision = cadence.delivery_decision(item)
    assert decision["mode"] == "progress"
    assert decision["formal_delivery_checkbox"] is False


def test_an_enabled_formal_checkbox_keeps_the_formal_channel(tmp_path):
    # Same room state, checkbox clickable (field absent, as on older snapshots): the
    # revision escalates to formal exactly as before.
    item = dict(
        _finished_order(tmp_path),
        formal_delivery_observed=True,
        talkroom_state="納品確認待ち",
    )
    assert cadence.delivery_decision(item)["mode"] == "formal"


def test_a_subscription_room_never_gets_a_one_shot_delivery(tmp_path):
    """B4 (spec section CC'): A5's room_contract_kind="subscription" (90000004/買い手C) must
    short-circuit every gate below -- an every-gate-passes finished order that would
    otherwise deliver "formal" (see test_without_a_parked_buyer_decision_a_finished_order_
    delivers_formally) instead lands on "none", matching today's measured live behaviour,
    unconditionally rather than by coincidence of unrelated branches (delivered_on_the_
    buyers_own_system / awaiting_buyer_decision) that happen to agree today.
    """
    base = _finished_order(tmp_path)
    item = dict(base, room_contract_kind="subscription")
    decision = cadence.delivery_decision(item)
    assert decision["mode"] == "none"
    assert decision["formal_delivery_checkbox"] is False
    assert decision["blockers"] == []

    # Even a revision mid-flight (the exact shape B3 routes to "progress" for a one-shot
    # room) must not fall through to "progress" here either -- a subscription room has no
    # progress-with-formal-semantics channel, only B1's ordinary reply lane.
    revision_shape = dict(
        base,
        room_contract_kind="subscription",
        formal_delivery_observed=True,
        talkroom_state="納品確認待ち",
        formal_delivery_control_disabled=True,
    )
    assert cadence.delivery_decision(revision_shape)["mode"] == "none"


def test_an_unknown_contract_kind_is_unchanged_from_before_a5(tmp_path):
    """A5 fail-closed default: "unknown" must behave exactly like the field's total absence
    -- it falls straight through to the pre-existing gates, never blocked by this guard.
    """
    base = _finished_order(tmp_path)
    absent = cadence.delivery_decision(base)
    unknown = cadence.delivery_decision(dict(base, room_contract_kind="unknown"))
    assert absent["mode"] == unknown["mode"] == "formal"


def test_a_one_shot_contract_kind_is_unchanged(tmp_path):
    item = dict(_finished_order(tmp_path), room_contract_kind="one_shot")
    assert cadence.delivery_decision(item)["mode"] == "formal"
