"""A4: the ledger row between "built" and "the buyer's world changed".

Measured 2026-08-07 22:20 on order 91000002: builder produced v5 with
acceptance PASS, the project ledger's last event was
``paid_work_ready_for_browser``, ``handled_buyer_feedback_sha256`` still held the
previous round's digest and ``latest_buyer_visible_version`` was v2.  Nothing in
the project said the artifact was sent and nothing said it was not, so the next
pass had to assume it had never happened and build v6.
"""

from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


delivery_attempt = _load("delivery_attempt")
project_ledger = _load("project_ledger")
delivery_cadence = _load("delivery_cadence")

FEEDBACK = "8" * 64
OTHER_FEEDBACK = "3" * 64
PACKAGE = "6" * 64


def _project(tmp_path, **state):
    root = project_ledger.init_project(tmp_path, "91000002", "coconala", dict(state))
    return Path(root)


def _state(root):
    return json.loads((root / "state.json").read_text(encoding="utf-8"))


def _events(root):
    return [
        json.loads(line)
        for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


# --------------------------------------------------------------------------
# identity
# --------------------------------------------------------------------------


def test_attempt_key_is_per_buyer_request_and_per_package_not_per_project():
    """A failure against v4 must never read as a failure against v5."""
    first = delivery_attempt.attempt_key(FEEDBACK, PACKAGE)
    assert first != delivery_attempt.attempt_key(OTHER_FEEDBACK, PACKAGE)
    assert first != delivery_attempt.attempt_key(FEEDBACK, "7" * 64)
    assert first == delivery_attempt.attempt_key(FEEDBACK.upper(), f"  {PACKAGE} ")


def test_a_malformed_digest_never_becomes_an_identity():
    assert delivery_attempt.attempt_key("not-a-digest", None) == "-:-"


# --------------------------------------------------------------------------
# the failure half
# --------------------------------------------------------------------------


def test_a_failed_delivery_is_recorded_in_the_project_not_only_the_pass(tmp_path):
    root = _project(tmp_path, current_version="v5", current_package_sha256=PACKAGE)

    report = delivery_attempt.record_failed(
        root,
        channel=delivery_attempt.CHANNEL_TALKROOM,
        reason="paid_queue_delivery_failed",
        buyer_feedback_sha256=FEEDBACK,
        pass_id="gig-pass-1786107605-99603",
    )

    assert [row["event"] for row in _events(root)][-1] == "delivery_attempt_failed"
    assert report["verdict"] == "tried_and_failed"
    assert report["failed_attempts"] == 1
    assert report["last_reason"] == "paid_queue_delivery_failed"
    state = _state(root)
    assert state["last_delivery_attempt_outcome"] == "failed"
    # The package the ledger holds, re-derived, not one supplied by a caller.
    assert state["delivery_attempts"][-1]["package_sha256"] == PACKAGE
    assert state["delivery_attempts"][-1]["artifact_version"] == "v5"


def test_never_tried_and_tried_three_times_are_different_answers(tmp_path):
    root = _project(tmp_path, current_package_sha256=PACKAGE)

    assert delivery_attempt.attempt_report(_state(root), FEEDBACK, PACKAGE) == {
        **delivery_attempt.attempt_report(_state(root), FEEDBACK, PACKAGE),
        "verdict": "never_tried",
        "failed_attempts": 0,
        "exhausted": False,
    }

    for _ in range(3):
        report = delivery_attempt.record_failed(
            root,
            channel=delivery_attempt.CHANNEL_TALKROOM,
            reason="browser_cdp_unavailable",
            buyer_feedback_sha256=FEEDBACK,
        )

    assert report["verdict"] == "tried_and_failed"
    assert report["failed_attempts"] == 3
    # E6b: retries without a terminus are cost, not recovery.
    assert report["exhausted"] is True


def test_a_failure_against_one_target_is_not_a_failure_against_the_next_build(tmp_path):
    root = _project(tmp_path, current_package_sha256=PACKAGE)
    delivery_attempt.record_failed(
        root, channel="talkroom", reason="paid_queue_delivery_failed",
        buyer_feedback_sha256=FEEDBACK,
    )

    fresh = delivery_attempt.attempt_report(_state(root), OTHER_FEEDBACK, PACKAGE)

    assert fresh["verdict"] == "never_tried"
    assert fresh["failed_attempts"] == 0


def test_free_text_from_a_page_never_reaches_the_append_only_row(tmp_path):
    """The reason vocabulary is ours. Remote text is dropped, not stored."""
    root = _project(tmp_path, current_package_sha256=PACKAGE)

    delivery_attempt.record_failed(
        root,
        channel="whatever-the-browser-said",
        reason="Error: <script>送信できませんでした</script>",
        buyer_feedback_sha256=FEEDBACK,
    )

    row = _state(root)["delivery_attempts"][-1]
    assert row["reason"] == delivery_attempt.UNKNOWN_REASON
    assert row["channel"] == delivery_attempt.CHANNEL_TALKROOM


def test_the_counter_survives_a_history_window_that_does_not(tmp_path):
    """A pruned zero must not read as "this never happened"."""
    root = _project(tmp_path, current_package_sha256=PACKAGE)
    for _ in range(delivery_attempt._HISTORY_LIMIT + 5):
        delivery_attempt.record_failed(
            root, channel="talkroom", reason="paid_queue_delivery_failed",
            buyer_feedback_sha256=FEEDBACK,
        )

    state = _state(root)
    report = delivery_attempt.attempt_report(state, FEEDBACK, PACKAGE)

    assert len(state["delivery_attempts"]) == delivery_attempt._HISTORY_LIMIT
    assert report["failed_attempts"] == delivery_attempt._HISTORY_LIMIT + 5
    assert report["history_truncated"] is True


def test_state_moves_only_through_the_ledger_api(tmp_path):
    """Every write appends an event; state.json is never edited behind it."""
    root = _project(tmp_path, current_package_sha256=PACKAGE)
    before = len(_events(root))

    delivery_attempt.record_failed(
        root, channel="talkroom", reason="paid_queue_delivery_failed",
        buyer_feedback_sha256=FEEDBACK,
    )

    events = _events(root)
    assert len(events) == before + 1
    assert events[-1]["state"] == _state(root)


def test_recording_against_an_uninitialised_project_refuses(tmp_path):
    (tmp_path / "91000002").mkdir()
    (tmp_path / "91000002" / "state.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError):
        delivery_attempt.record_failed(
            tmp_path / "91000002", channel="talkroom", reason="x",
            buyer_feedback_sha256=FEEDBACK,
        )


# --------------------------------------------------------------------------
# the confirmed half
# --------------------------------------------------------------------------


def test_the_digest_advances_on_confirmation_and_clears_the_failure_count(tmp_path):
    root = _project(tmp_path, current_package_sha256=PACKAGE)
    for _ in range(2):
        delivery_attempt.record_failed(
            root, channel="talkroom", reason="paid_queue_delivery_failed",
            buyer_feedback_sha256=FEEDBACK,
        )

    patch = delivery_attempt.confirmed_patch(
        _state(root), channel="talkroom", buyer_feedback_sha256=FEEDBACK,
        package_sha256=PACKAGE, artifact_version="v5",
    )
    project_ledger.append(root, patch, "paid_work_browser_sent_reconciled")

    state = _state(root)
    assert state["handled_buyer_feedback_sha256"] == FEEDBACK
    assert state["delivery_confirmed_feedback_sha256"] == FEEDBACK
    assert delivery_attempt.attempt_report(state, FEEDBACK, PACKAGE)["verdict"] == "confirmed"
    assert delivery_attempt.attempt_report(state, FEEDBACK, PACKAGE)["failed_attempts"] == 0


def test_an_unnamed_buyer_request_leaves_the_digest_alone_and_says_why(tmp_path):
    root = _project(tmp_path, handled_buyer_feedback_sha256=OTHER_FEEDBACK)

    patch = delivery_attempt.confirmed_patch(
        _state(root), channel="talkroom", buyer_feedback_sha256="",
        package_sha256=PACKAGE, artifact_version="v5",
    )
    project_ledger.append(root, patch, "paid_work_browser_sent_reconciled")

    state = _state(root)
    assert state["handled_buyer_feedback_sha256"] == OTHER_FEEDBACK
    assert state["delivery_digest_unadvanced_reason"] == "buyer_request_not_named_by_queue_item"


def test_a_hand_written_handled_digest_is_not_a_confirmed_delivery(tmp_path):
    """90000004 carries one, and task #21 records that it is stale.

    Only a delivery this module confirmed may answer ``confirmed_for_feedback``,
    so no pre-existing project is retroactively declared delivered.
    """
    root = _project(tmp_path)
    project_ledger.append(root, {
        "work_state": "DELIVERED",
        "next_action": "await_buyer_decision",
        "delivery_channel": "live_system",
        "handled_buyer_feedback_sha256": FEEDBACK,
    }, "live_system_delivery_recorded")

    assert delivery_attempt.confirmed_for_feedback(_state(root), FEEDBACK) is False


def test_the_row_is_true_for_a_delivery_that_was_not_a_file_in_a_room(tmp_path):
    """90000004's channel: the buyer's own site changed. Still a delivery."""
    root = _project(tmp_path)

    patch = delivery_attempt.confirmed_patch(
        _state(root), channel=delivery_attempt.CHANNEL_LIVE_SYSTEM,
        buyer_feedback_sha256=FEEDBACK,
    )
    project_ledger.append(root, patch, "live_system_delivery_recorded")

    state = _state(root)
    assert state["delivery_channel"] == "live_system"
    assert delivery_attempt.confirmed_for_feedback(state, FEEDBACK) is True
    assert state["delivery_attempts"][-1]["package_sha256"] is None


# --------------------------------------------------------------------------
# the consumer: a recorded delivery ends the rebuild
# --------------------------------------------------------------------------


def _cadence_item(root, *, feedback, artifact, requirements, observed_at):
    requirements.write_text(json.dumps({
        "feedback_sha256": feedback,
        "observed_at": observed_at,
    }) + "\n", encoding="utf-8")
    return {
        "project_root": str(root),
        "buyer_feedback_sha256": feedback,
        "requirements_path": str(requirements),
        "artifact_path": str(artifact),
    }


def test_a_confirmed_delivery_ends_the_rebuild_even_when_the_room_was_re_read(tmp_path):
    """91000002: the sidecar was rewritten at 22:21 with a fresh observed_at
    while v5, built at 22:07 for that same request, sat undelivered -- so the
    artifact was retroactively older than the request it answered."""
    root = _project(tmp_path, current_package_sha256=PACKAGE)
    artifact = tmp_path / "v5.zip"
    artifact.write_bytes(b"artifact")
    requirements = tmp_path / "live-buyer-reply.json"
    later = time.strftime(
        "%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(artifact.stat().st_mtime + 720),
    )
    item = _cadence_item(
        root, feedback=FEEDBACK, artifact=artifact,
        requirements=requirements, observed_at=later,
    )

    assert delivery_cadence._buyer_feedback_processed(item) is False

    project_ledger.append(root, delivery_attempt.confirmed_patch(
        _state(root), channel="talkroom", buyer_feedback_sha256=FEEDBACK,
        package_sha256=PACKAGE, artifact_version="v5",
    ), "paid_work_browser_sent_reconciled")

    assert delivery_cadence._buyer_feedback_processed(item) is True


def test_a_failed_delivery_does_not_end_the_rebuild(tmp_path):
    """The reverse. A built-but-unsent artifact must stay unprocessed."""
    root = _project(tmp_path, current_package_sha256=PACKAGE)
    artifact = tmp_path / "v5.zip"
    artifact.write_bytes(b"artifact")
    requirements = tmp_path / "live-buyer-reply.json"
    later = time.strftime(
        "%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(artifact.stat().st_mtime + 720),
    )
    item = _cadence_item(
        root, feedback=FEEDBACK, artifact=artifact,
        requirements=requirements, observed_at=later,
    )

    for _ in range(3):
        delivery_attempt.record_failed(
            root, channel="talkroom", reason="paid_queue_delivery_failed",
            buyer_feedback_sha256=FEEDBACK,
        )

    assert _state(root).get("handled_buyer_feedback_sha256") is None
    assert delivery_cadence._buyer_feedback_processed(item) is False
    assert delivery_cadence.delivery_decision({
        **item,
        "buyer_reply_after_artifact_observed": True,
        "blockers": [],
    })["mode"] == "work_required"


def test_a_new_buyer_message_reopens_a_delivered_request(tmp_path):
    root = _project(tmp_path, current_package_sha256=PACKAGE)
    artifact = tmp_path / "v5.zip"
    artifact.write_bytes(b"artifact")
    requirements = tmp_path / "live-buyer-reply.json"
    project_ledger.append(root, delivery_attempt.confirmed_patch(
        _state(root), channel="talkroom", buyer_feedback_sha256=FEEDBACK,
        package_sha256=PACKAGE, artifact_version="v5",
    ), "paid_work_browser_sent_reconciled")

    reopened = _cadence_item(
        root, feedback=OTHER_FEEDBACK, artifact=artifact,
        requirements=requirements,
        observed_at=time.strftime(
            "%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(artifact.stat().st_mtime + 720),
        ),
    )

    assert delivery_cadence._buyer_feedback_processed(reopened) is False


def test_an_unreadable_project_never_claims_a_delivery(tmp_path):
    item = {
        "project_root": str(tmp_path / "does-not-exist"),
        "buyer_feedback_sha256": FEEDBACK,
        "requirements_path": "",
        "artifact_path": "",
    }
    assert delivery_cadence._buyer_feedback_processed(item) is False


# --------------------------------------------------------------------------
# the erratum: failures that were never attempts (order 91000002, 2026-08-08)
# --------------------------------------------------------------------------


def test_a_correction_reopens_the_window_without_claiming_a_delivery(tmp_path):
    """9 recorded failures were validation crashes that never opened a browser tab.

    The correction supersedes them: count back to zero, verdict back to never_tried,
    exhausted off -- while the handled/confirmed digests stay untouched, because
    nothing was delivered and nothing may claim to be.
    """
    root = _project(tmp_path, current_version="v6", current_package_sha256=PACKAGE)
    for _ in range(3):
        delivery_attempt.record_failed(
            root,
            channel=delivery_attempt.CHANNEL_TALKROOM,
            reason="paid_queue_delivery_failed",
            buyer_feedback_sha256=FEEDBACK,
        )
    exhausted = delivery_attempt.attempt_report(_state(root), FEEDBACK, PACKAGE)
    assert exhausted["exhausted"] is True

    report = delivery_attempt.record_correction(
        root,
        reason="validation_crash_consumed_attempts",
        buyer_feedback_sha256=FEEDBACK,
    )

    assert report["failed_attempts"] == 0
    assert report["verdict"] == "never_tried"
    assert report["exhausted"] is False
    state = _state(root)
    assert state["last_delivery_attempt_outcome"] == "corrected"
    assert "handled_buyer_feedback_sha256" not in state
    assert "delivery_confirmed_feedback_sha256" not in state
    assert _events(root)[-1]["event"] == "delivery_attempt_correction"
    # The correction row itself is durable history, not an erasure.
    assert state["delivery_attempts"][-1]["outcome"] == "corrected"
    assert state["delivery_attempts"][-1]["reason"] == "validation_crash_consumed_attempts"


def test_the_correction_event_counts_as_progress_for_admission(tmp_path):
    """paid_admission's INERT_EVENTS is a denylist; the correction is deliberately not on
    it, so a corrected order stops reading as stalled and is admitted to retry."""
    paid_admission = _load("paid_admission")
    assert "delivery_attempt_correction" not in paid_admission.INERT_EVENTS
    root = _project(tmp_path, current_version="v6", current_package_sha256=PACKAGE)
    project_ledger.append(root, {}, "queue_selected")
    delivery_attempt.record_failed(
        root, channel="talkroom", reason="paid_queue_delivery_failed",
        buyer_feedback_sha256=FEEDBACK,
    )
    project_ledger.append(root, {}, "queue_selected")
    delivery_attempt.record_failed(
        root, channel="talkroom", reason="paid_queue_delivery_failed",
        buyer_feedback_sha256=FEEDBACK,
    )
    rows = paid_admission.read_events(tmp_path, "91000002")
    # The second identical failure reason is inert (a repeat), the first is not, so the
    # backwards walk stops there: one barren selection is on the books before the fix.
    assert paid_admission.selections_without_progress(rows) == 1

    delivery_attempt.record_correction(
        root, reason="validation_crash_consumed_attempts",
        buyer_feedback_sha256=FEEDBACK,
    )
    rows = paid_admission.read_events(tmp_path, "91000002")
    assert paid_admission.selections_without_progress(rows) == 0
