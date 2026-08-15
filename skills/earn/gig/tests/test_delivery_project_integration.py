import json
import os
import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import delivery_project
import paid_admission


def accepted_artifact_fixture(tmp_path, *, buyer_visible):
    root = delivery_project.record_queue_selection(
        tmp_path,
        {"request_id": "req-42", "buyer": "Buyer"},
        adapter="coconala",
    )
    requirements = root / "requirements" / "feedback.json"
    requirements.write_text(json.dumps({
        "observed_at": "2020-01-01T00:00:00+00:00",
        "feedback_sha256": "a" * 64,
    }) + "\n")
    artifact = root / "artifacts" / "delivery-v7.zip"
    artifact.write_bytes(b"accepted-v7")
    package_hash = hashlib.sha256(artifact.read_bytes()).hexdigest()
    acceptance = root / "acceptance" / "v7.json"
    acceptance.write_text('{"status":"PASS"}\n')
    stable_path = tmp_path / "delivery-evidence.json"
    stable = {
        "status": "ok",
        "project_root": str(root),
        "requirements_path": str(requirements),
        "artifact_path": str(artifact),
        "artifact_version": "v7",
        "acceptance_evidence_path": str(acceptance),
        "acceptance_status": "PASS",
        "acceptance_delta": ["accepted"],
        "package_sha256": package_hash,
    }
    stable_path.write_text(json.dumps(stable) + "\n")
    state = {
        "current_version": "v7",
        "current_artifact_path": str(artifact),
        "current_package_sha256": package_hash,
        "current_acceptance_evidence_path": str(acceptance),
        "current_acceptance_status": "PASS",
        "current_acceptance_delta": ["accepted"],
        "current_delivery_evidence_path": str(stable_path),
        "current_delivery_evidence_mtime": stable_path.stat().st_mtime,
        "buyer_visible": buyer_visible,
        "artifact_ready_pending_browser": not buyer_visible,
        "next_action": "await_buyer_feedback" if buyer_visible else "retry_buyer_visible_delivery",
    }
    if buyer_visible:
        state.update({
            "latest_buyer_visible_version": "v7",
            "latest_buyer_visible_package_sha256": package_hash,
        })
    delivery_project.project_ledger.append(root, state, "accepted_artifact_fixture")
    item = {
        "talkroom_state": "取引中",
        "buyer_feedback_pending_artifact": True,
        "buyer_reply_after_artifact_observed": True,
        "buyer_visible_artifact_observed": buyer_visible,
        "buyer_feedback_sha256": "a" * 64,
        "buyer_feedback_requirements_path": str(requirements),
        "delivery_evidence": {
            "path": str(stable_path),
            "present": True,
            **stable,
        },
    }
    return root, item


def test_queue_item_creates_request_scoped_ledger(tmp_path):
    item = {"request_id": "req-42", "buyer": "Buyer", "price_jpy": 65000}
    root = delivery_project.record_queue_selection(tmp_path, item, adapter="coconala")
    state = json.loads((root / "state.json").read_text())
    assert state["request_id"] == "req-42"
    assert state["adapter"] == "coconala"
    assert state["next_action"] == "delivery_evidence"
    assert (root / "events.jsonl").read_text().count("queue_selected") == 1


def test_queue_selection_persists_valid_buyer_feedback_hash(tmp_path):
    feedback = "a" * 64
    root = delivery_project.record_queue_selection(
        tmp_path,
        {"request_id": "req-42", "buyer": "Buyer", "buyer_feedback_sha256": feedback},
        adapter="coconala",
    )
    rows = [json.loads(line) for line in (root / "events.jsonl").read_text().splitlines()]
    selected = next(row for row in rows if row["event"] == "queue_selected")
    assert selected["state"]["buyer_feedback_sha256"] == feedback


def _expected_feedback_cycle(talkroom_id, feedback, *, phase="ACTIONABLE"):
    return {
        "version": 1, "key": f"coconala:{talkroom_id}:{feedback}",
        "talkroom_id": talkroom_id, "buyer_feedback_sha256": feedback,
        "action": "resubmit", "phase": phase,
        "effect_key": f"coconala:{talkroom_id}:{feedback}:resubmit",
    }


def test_valid_feedback_creates_exact_resubmission_cycle(tmp_path):
    feedback = "a" * 64
    root = delivery_project.record_queue_selection(
        tmp_path, {"request_id": "req-42", "talkroom_id": "room-42", "buyer_feedback_sha256": feedback}, adapter="coconala"
    )
    state = json.loads((root / "state.json").read_text())
    assert state["active_feedback_cycle"] == _expected_feedback_cycle("room-42", feedback)
    assert state["feedback_cycle_count"] == 1


def test_same_feedback_is_idempotent_and_preserves_advanced_phase(tmp_path):
    feedback = "a" * 64
    item = {"request_id": "req-42", "talkroom_id": "room-42", "buyer_feedback_sha256": feedback}
    root = delivery_project.record_queue_selection(tmp_path, item, adapter="coconala")
    advanced = _expected_feedback_cycle("room-42", feedback, phase="WORKING")
    delivery_project.project_ledger.append(root, {"active_feedback_cycle": advanced, "feedback_cycle_count": 1}, "phase_advanced")
    delivery_project.record_queue_selection(tmp_path, item, adapter="coconala")
    state = json.loads((root / "state.json").read_text())
    assert state["active_feedback_cycle"] == advanced
    assert state["feedback_cycle_count"] == 1


def test_new_feedback_creates_new_identity_and_increments_count(tmp_path):
    first, second = "a" * 64, "b" * 64
    item = {"request_id": "req-42", "talkroom_id": "room-42"}
    root = delivery_project.record_queue_selection(tmp_path, {**item, "buyer_feedback_sha256": first}, adapter="coconala")
    delivery_project.record_queue_selection(tmp_path, {**item, "buyer_feedback_sha256": second}, adapter="coconala")
    state = json.loads((root / "state.json").read_text())
    assert state["active_feedback_cycle"] == _expected_feedback_cycle("room-42", second)
    assert state["feedback_cycle_count"] == 2


def test_invalid_feedback_and_missing_talkroom_never_create_or_erase_cycle(tmp_path):
    feedback = "a" * 64
    item = {"request_id": "req-42", "talkroom_id": "room-42", "buyer_feedback_sha256": feedback}
    root = delivery_project.record_queue_selection(tmp_path, item, adapter="coconala")
    expected = json.loads((root / "state.json").read_text())
    for invalid in ({"request_id": "req-42", "talkroom_id": "room-42"}, {"request_id": "req-42", "talkroom_id": "room-42", "buyer_feedback_sha256": "bad"}, {"request_id": "req-42", "buyer_feedback_sha256": "b" * 64}):
        delivery_project.record_queue_selection(tmp_path, invalid, adapter="coconala")
        state = json.loads((root / "state.json").read_text())
        assert state["active_feedback_cycle"] == expected["active_feedback_cycle"]
        assert state["feedback_cycle_count"] == expected["feedback_cycle_count"]
    for index, invalid in enumerate(({"request_id": "req-fresh"}, {"request_id": "req-fresh", "buyer_feedback_sha256": "bad"}, {"request_id": "req-fresh", "buyer_feedback_sha256": "b" * 64})):
        fresh = delivery_project.record_queue_selection(tmp_path / f"fresh-{index}", invalid, adapter="coconala")
        fresh_state = json.loads((fresh / "state.json").read_text())
        assert "active_feedback_cycle" not in fresh_state and "feedback_cycle_count" not in fresh_state


def test_feedback_cycle_event_state_excludes_buyer_message_body(tmp_path):
    root = delivery_project.record_queue_selection(tmp_path, {
        "request_id": "req-42", "talkroom_id": "room-42", "buyer_feedback_sha256": "a" * 64,
        "buyer_feedback_message": "PRIVATE BUYER MESSAGE", "buyer_feedback_body": "PRIVATE BUYER BODY",
    }, adapter="coconala")
    events = (root / "events.jsonl").read_text()
    assert "PRIVATE BUYER MESSAGE" not in events and "PRIVATE BUYER BODY" not in events


def test_new_project_selection_hash_is_observed_by_same_hash_plan(tmp_path):
    feedback = "a" * 64
    item = {"request_id": "req-42", "buyer": "Buyer", "buyer_feedback_sha256": feedback}
    for _ in range(23):
        root = delivery_project.record_queue_selection(tmp_path, item, adapter="coconala")
    selected = [
        json.loads(line) for line in (root / "events.jsonl").read_text().splitlines()
        if json.loads(line)["event"] == "queue_selected"
    ]
    assert selected[0]["state"]["buyer_feedback_sha256"] == feedback
    planned = paid_admission.plan([item], projects_root=tmp_path)
    assert planned["skipped"] == ["req-42"]
    assert planned["decisions"][0]["selections_without_progress"] == 23


def test_missing_request_id_is_rejected(tmp_path):
    try:
        delivery_project.record_queue_selection(tmp_path, {"buyer": "Buyer"}, adapter="coconala")
    except ValueError as exc:
        assert "request_id" in str(exc)
    else:
        raise AssertionError("missing request_id must fail closed")


def test_talkroom_reuses_unique_existing_request_project(tmp_path):
    existing = delivery_project.record_queue_selection(
        tmp_path,
        {"request_id": "req-existing", "talkroom_id": "room-42", "buyer": "Buyer"},
        adapter="coconala",
    )

    reused = delivery_project.record_queue_selection(
        tmp_path,
        {"talkroom_id": "room-42", "buyer": "Buyer"},
        adapter="coconala",
    )

    assert reused == existing
    state = json.loads((existing / "state.json").read_text())
    assert state["request_id"] == "req-existing"


def test_ambiguous_talkroom_matches_fail_closed(tmp_path):
    for request_id in ("req-one", "req-two"):
        delivery_project.record_queue_selection(
            tmp_path,
            {"request_id": request_id, "talkroom_id": "room-ambiguous", "buyer": "Buyer"},
            adapter="coconala",
        )

    try:
        delivery_project.record_queue_selection(
            tmp_path,
            {"talkroom_id": "room-ambiguous", "buyer": "Buyer"},
            adapter="coconala",
        )
    except ValueError as exc:
        assert "ambiguous" in str(exc).lower()
    else:
        raise AssertionError("ambiguous talkroom identity must fail closed")
    assert not (tmp_path / "room-ambiguous").exists()


def test_explicit_request_id_takes_precedence_over_talkroom_reuse(tmp_path):
    delivery_project.record_queue_selection(
        tmp_path,
        {"request_id": "req-existing", "talkroom_id": "room-42", "buyer": "Buyer"},
        adapter="coconala",
    )

    selected = delivery_project.record_queue_selection(
        tmp_path,
        {"request_id": "req-explicit", "talkroom_id": "room-42", "buyer": "Buyer"},
        adapter="coconala",
    )

    assert selected == tmp_path / "req-explicit"
    assert (selected / "state.json").exists()


def test_unmatched_talkroom_keeps_safe_talkroom_fallback(tmp_path):
    selected = delivery_project.record_queue_selection(
        tmp_path,
        {"talkroom_id": "room-new", "contract_id": "direct-offer:1", "buyer": "Buyer"},
        adapter="coconala",
    )

    assert selected == tmp_path / "room-new"
    state = json.loads((selected / "state.json").read_text())
    assert state["request_id"] == "room-new"


def test_preliminary_project_resolution_does_not_mutate_awaiting_ledger(tmp_path):
    root = delivery_project.record_queue_selection(
        tmp_path,
        {"request_id": "req-await", "talkroom_id": "room-await", "buyer": "Buyer"},
        adapter="coconala",
    )
    delivery_project.project_ledger.append(root, {
        "buyer_visible": True,
        "next_action": "await_buyer_decision",
        "handled_buyer_feedback_sha256": "a" * 64,
    }, "buyer_wait_recorded")
    state_before = (root / "state.json").read_bytes()
    events_before = (root / "events.jsonl").read_bytes()

    preliminary = {
        "request_id": "req-await",
        "talkroom_id": "room-await",
        "buyer": "Buyer",
        "buyer_feedback_pending_artifact": True,
        "buyer_feedback_sha256": "b" * 64,
        "selection_stage": "preliminary",
        "targeted_readback_required": True,
    }

    assert delivery_project.resolve_project_root(tmp_path, preliminary) == root
    assert (root / "state.json").read_bytes() == state_before
    assert (root / "events.jsonl").read_bytes() == events_before


def test_targeted_feedback_reopens_existing_awaiting_project(tmp_path):
    root = delivery_project.record_queue_selection(
        tmp_path,
        {"request_id": "req-targeted", "talkroom_id": "room-targeted", "buyer": "Buyer"},
        adapter="coconala",
    )
    delivery_project.project_ledger.append(root, {
        "buyer_visible": True,
        "next_action": "await_buyer_decision",
        "handled_buyer_feedback_sha256": "a" * 64,
    }, "buyer_wait_recorded")
    targeted = {
        "request_id": "req-targeted",
        "talkroom_id": "room-targeted",
        "buyer": "Buyer",
        "buyer_feedback_pending_artifact": True,
        "buyer_feedback_sha256": "b" * 64,
        "selection_stage": "targeted",
        "targeted_readback_required": False,
        "delivery_action": "none",
    }

    assert delivery_project.record_queue_selection(
        tmp_path, targeted, adapter="coconala",
    ) == root
    assert delivery_project.resolve_workflow_action(root, targeted) == "act"


def test_inconsistent_state_root_is_not_a_talkroom_match(tmp_path):
    root = tmp_path / "req-root"
    root.mkdir()
    (root / "state.json").write_text(json.dumps({
        "request_id": "req-other",
        "adapter": "coconala",
        "talkroom_id": "room-inconsistent",
    }) + "\n")

    selected = delivery_project.record_queue_selection(
        tmp_path,
        {"talkroom_id": "room-inconsistent", "buyer": "Buyer"},
        adapter="coconala",
    )

    assert selected == tmp_path / "room-inconsistent"


def test_direct_offer_falls_back_to_talkroom_and_preserves_existing_wait_state(tmp_path):
    root = delivery_project.record_queue_selection(tmp_path, {
        "contract_id": "direct-offer:92000003",
        "talkroom_id": "90000000",
        "buyer": "Buyer",
        "buyer_visible_artifact_observed": True,
        "buyer_feedback_pending_artifact": False,
        "buyer_agreement_observed": False,
        "talkroom_state": "取引中",
    }, adapter="coconala")
    assert root == tmp_path / "90000000"
    delivery_project.project_ledger.append(root, {
        "buyer_visible": True,
        "formal_delivery": False,
        "next_action": "await_buyer_approval_for_publication",
    }, "review_artifact_sent")

    root = delivery_project.record_queue_selection(tmp_path, {
        "contract_id": "direct-offer:92000003",
        "talkroom_id": "90000000",
        "buyer": "Buyer",
        "buyer_visible_artifact_observed": True,
        "buyer_feedback_pending_artifact": False,
        "buyer_agreement_observed": False,
        "talkroom_state": "取引中",
    }, adapter="coconala")
    state = json.loads((root / "state.json").read_text())
    assert state["request_id"] == "90000000"
    assert state["source_contract_id"] == "direct-offer:92000003"
    assert state["next_action"] == "await_buyer_approval_for_publication"
    assert delivery_project.workflow_action(root, {
        "buyer_visible_artifact_observed": True,
        "buyer_feedback_pending_artifact": False,
        "buyer_agreement_observed": False,
        "talkroom_state": "取引中",
    }) == "await_buyer"


def test_buyer_reply_reopens_waiting_project(tmp_path):
    root = delivery_project.record_queue_selection(tmp_path, {
        "request_id": "req-42", "talkroom_id": "42", "buyer": "Buyer",
    }, adapter="coconala")
    delivery_project.project_ledger.append(root, {
        "buyer_visible": True,
        "next_action": "await_buyer_approval_for_publication",
    }, "review_artifact_sent")
    for live_delta in (
        {"buyer_feedback_pending_artifact": True, "buyer_visible_artifact_observed": True},
        {"buyer_agreement_observed": True, "buyer_visible_artifact_observed": True},
        {"buyer_reply_after_artifact_observed": True, "buyer_visible_artifact_observed": True},
    ):
        assert delivery_project.workflow_action(root, {
            "talkroom_state": "取引中",
            "buyer_feedback_pending_artifact": False,
            "buyer_agreement_observed": False,
            "buyer_reply_after_artifact_observed": False,
            **live_delta,
        }) == "act"


def test_queue_poll_does_not_erase_durable_price_when_observation_is_ambiguous(tmp_path):
    root = delivery_project.record_queue_selection(
        tmp_path,
        {"request_id": "req-42", "buyer": "Buyer", "price_jpy": 40000},
        adapter="coconala",
    )
    delivery_project.record_queue_selection(
        tmp_path,
        {
            "request_id": "req-42",
            "buyer": "Buyer",
            "price_jpy": None,
            "price_source": "ambiguous_card_text",
        },
        adapter="coconala",
    )
    state = json.loads((root / "state.json").read_text())
    assert state["price_jpy"] == 40000


def test_valid_pending_browser_delivery_is_reused_without_rebuilding(tmp_path):
    root = delivery_project.record_queue_selection(
        tmp_path,
        {"request_id": "req-42", "buyer": "Buyer"},
        adapter="coconala",
    )
    delivery_project.project_ledger.append(root, {
        "current_version": "v3",
        "current_artifact_path": str(root / "artifacts" / "delivery-v3.zip"),
        "current_package_sha256": "a" * 64,
        "current_acceptance_evidence_path": str(root / "acceptance" / "v3.json"),
        "current_acceptance_status": "PASS",
        "current_acceptance_delta": ["fixed"],
        "buyer_visible": False,
        "artifact_ready_pending_browser": True,
        "next_action": "retry_buyer_visible_delivery",
    }, "paid_work_ready_for_browser")
    stable_path = tmp_path / "delivery-evidence.json"
    stable_path.write_text(json.dumps({
        "status": "ok", "project_root": str(root),
        "artifact_path": str(root / "artifacts" / "delivery-v3.zip"),
        "artifact_version": "v3",
        "acceptance_evidence_path": str(root / "acceptance" / "v3.json"),
        "acceptance_status": "PASS", "acceptance_delta": ["fixed"],
        "package_sha256": "a" * 64,
    }) + "\n")
    delivery_project.project_ledger.append(root, {
        "current_delivery_evidence_path": str(stable_path),
        "current_delivery_evidence_mtime": stable_path.stat().st_mtime,
    }, "paid_work_ready_evidence_bound")
    item = {
        "buyer_feedback_pending_artifact": True,
        "delivery_evidence": {
            "path": str(stable_path),
            "present": True,
            "status": "ok",
            "project_root": str(root),
            "artifact_path": str(root / "artifacts" / "delivery-v3.zip"),
            "artifact_version": "v3",
            "acceptance_evidence_path": str(root / "acceptance" / "v3.json"),
            "acceptance_status": "PASS",
            "acceptance_delta": ["fixed"],
            "package_sha256": "a" * 64,
        },
    }
    assert delivery_project.workflow_action(root, item) == "deliver_existing"

    for key, value in (("package_sha256", "b" * 64), ("artifact_version", "v4")):
        mismatched = {**item, "delivery_evidence": {**item["delivery_evidence"], key: value}}
        assert delivery_project.workflow_action(root, mismatched) == "act"
    for key, value in (("present", False), ("status", "invalid")):
        invalid = {**item, "delivery_evidence": {**item["delivery_evidence"], key: value}}
        assert delivery_project.workflow_action(root, invalid) == "act"
    os.utime(stable_path, (1, 1))
    assert delivery_project.workflow_action(root, item) == "act"


def test_accepted_artifact_bootstraps_feedback_idempotency_without_rebuilding(tmp_path):
    root, item = accepted_artifact_fixture(tmp_path, buyer_visible=False)

    assert delivery_project.resolve_workflow_action(root, item) == "deliver_existing"
    state = json.loads((root / "state.json").read_text())
    assert state["handled_buyer_feedback_sha256"] == "a" * 64
    assert state["material_event_outcome"] == "accepted_artifact_reconciled"

    assert delivery_project.resolve_workflow_action(root, item) == "deliver_existing"
    events = [
        json.loads(line)
        for line in (root / "events.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert [event["event"] for event in events].count("feedback_idempotency_bootstrapped") == 1


def test_delivered_artifact_with_unchanged_feedback_awaits_buyer(tmp_path):
    root, item = accepted_artifact_fixture(tmp_path, buyer_visible=True)

    assert delivery_project.resolve_workflow_action(root, item) == "await_buyer"
    state = json.loads((root / "state.json").read_text())
    assert state["handled_buyer_feedback_sha256"] == "a" * 64


def test_verified_answer_cannot_override_authoritative_progress_action(tmp_path):
    root, item = accepted_artifact_fixture(tmp_path, buyer_visible=False)
    state = json.loads((root / "state.json").read_text())
    state.update({
        "handled_buyer_feedback_sha256": item["buyer_feedback_sha256"],
        "material_event_outcome": "buyer_answer_sent",
        "last_buyer_answer_sha256": "c" * 64,
    })
    (root / "state.json").write_text(json.dumps(state) + "\n")
    item = {
        **item,
        "buyer_visible_artifact_observed": False,
        "buyer_feedback_pending_artifact": True,
        "buyer_reply_after_artifact_observed": True,
        "delivery_action": "progress",
    }

    assert delivery_project.resolve_workflow_action(root, item) == "deliver_existing"
    assert delivery_project.resolve_workflow_action(
        root, {**item, "buyer_feedback_sha256": "d" * 64}
    ) == "act"


def test_answered_status_update_does_not_force_rebuild_of_bound_artifact(tmp_path):
    root, item = accepted_artifact_fixture(tmp_path, buyer_visible=True)
    artifact = Path(item["delivery_evidence"]["artifact_path"])
    feedback_time = datetime.fromtimestamp(
        artifact.stat().st_mtime + 60, timezone.utc,
    ).isoformat()
    Path(item["buyer_feedback_requirements_path"]).write_text(json.dumps({
        "observed_at": feedback_time,
        "feedback_sha256": item["buyer_feedback_sha256"],
    }) + "\n")
    state = json.loads((root / "state.json").read_text())
    state.update({
        "handled_buyer_feedback_sha256": item["buyer_feedback_sha256"],
        "material_event_outcome": "buyer_answer_sent",
        "last_buyer_answer_sha256": "c" * 64,
    })
    (root / "state.json").write_text(json.dumps(state) + "\n")
    item = {
        **item,
        "buyer_visible_artifact_observed": False,
        "buyer_feedback_pending_artifact": True,
        "buyer_reply_after_artifact_observed": True,
        "delivery_action": "progress",
    }

    assert delivery_project.resolve_workflow_action(root, item) == "deliver_existing"
    state = json.loads((root / "state.json").read_text())
    assert state["buyer_visible"] is False
    assert state["artifact_ready_pending_browser"] is True
    assert state["next_action"] == "retry_buyer_visible_delivery"


def test_verified_answer_awaits_only_when_live_queue_requires_no_action(tmp_path):
    root, item = accepted_artifact_fixture(tmp_path, buyer_visible=False)
    state = json.loads((root / "state.json").read_text())
    state.update({
        "handled_buyer_feedback_sha256": item["buyer_feedback_sha256"],
        "material_event_outcome": "buyer_answer_sent",
        "last_buyer_answer_sha256": "c" * 64,
    })
    (root / "state.json").write_text(json.dumps(state) + "\n")

    assert delivery_project.resolve_workflow_action(
        root, {**item, "delivery_action": "none"}
    ) == "await_buyer"


def test_stale_buyer_visible_ledger_cannot_override_authoritative_live_absence(tmp_path):
    root, item = accepted_artifact_fixture(tmp_path, buyer_visible=True)
    item = {
        **item,
        "buyer_visible_artifact_observed": False,
        "buyer_feedback_pending_artifact": True,
        "buyer_reply_after_artifact_observed": True,
    }

    assert delivery_project.resolve_workflow_action(root, item) == "deliver_existing"
    state = json.loads((root / "state.json").read_text())
    assert state["buyer_visible"] is False
    assert state["artifact_ready_pending_browser"] is True
    assert state["next_action"] == "retry_buyer_visible_delivery"


def test_artifact_older_than_current_feedback_cannot_be_reused(tmp_path):
    root, item = accepted_artifact_fixture(tmp_path, buyer_visible=False)
    artifact = Path(item["delivery_evidence"]["artifact_path"])
    feedback_time = datetime.fromtimestamp(
        artifact.stat().st_mtime + 60, timezone.utc,
    ).isoformat()
    Path(item["buyer_feedback_requirements_path"]).write_text(json.dumps({
        "observed_at": feedback_time,
        "feedback_sha256": item["buyer_feedback_sha256"],
    }) + "\n")

    assert delivery_project.resolve_workflow_action(root, item) == "act"
    state = json.loads((root / "state.json").read_text())
    assert state.get("handled_buyer_feedback_sha256") is None


def test_new_buyer_revision_reopens_accepted_artifact_project_once(tmp_path):
    root, item = accepted_artifact_fixture(tmp_path, buyer_visible=True)
    assert delivery_project.resolve_workflow_action(root, item) == "await_buyer"

    revised = {**item, "buyer_feedback_sha256": "b" * 64}
    assert delivery_project.resolve_workflow_action(root, revised) == "act"


def _delivered_awaiting_buyer(tmp_path, *, handled="a" * 64):
    """A project whose ledger already concluded the ball is with the buyer."""
    root = delivery_project.record_queue_selection(
        tmp_path, {"request_id": "req-90000004", "buyer": "Buyer"}, adapter="coconala",
    )
    delivery_project.project_ledger.append(root, {
        "work_state": "DELIVERED",
        "next_action": "await_buyer_decision",
        "buyer_visible": False,
        "handled_buyer_feedback_sha256": handled,
    }, "live_system_delivery_recorded")
    return root


def _polled(request_id="req-90000004", **overrides):
    item = {
        "request_id": request_id,
        "buyer": "Buyer",
        "queue_class": "buyer_feedback_or_revision",
        "talkroom_state": "unknown",
        "buyer_feedback_pending_artifact": True,
        "delivery_action": "work_required",
    }
    item.update(overrides)
    return item


def test_re_observing_the_same_buyer_fact_never_erases_a_recorded_decision(tmp_path):
    """Order 90000004, 2026-08-07: reset at 09:01, 11:01, 12:01 and 20:02.

    The queue item carried ``buyer_feedback_pending_artifact`` with no
    ``buyer_feedback_sha256``, so it was permanently ``work_required``, and each
    poll wrote WORK_REQUIRED over a DELIVERED/await_buyer_decision ledger. The
    builder produced v15, v16 and v17 behind it.
    """
    root = _delivered_awaiting_buyer(tmp_path)
    for _ in range(3):
        delivery_project.record_queue_selection(tmp_path, _polled(), adapter="coconala")
    state = json.loads((root / "state.json").read_text())
    assert state["work_state"] == "DELIVERED"
    assert state["next_action"] == "await_buyer_decision"
    # The observations themselves still land.
    assert state["buyer_feedback_pending_artifact"] is True
    assert state["queue_class"] == "buyer_feedback_or_revision"


def test_a_buyer_fact_we_have_not_handled_still_moves_a_delivered_order_into_work(tmp_path):
    root = _delivered_awaiting_buyer(tmp_path, handled="a" * 64)
    delivery_project.record_queue_selection(
        tmp_path, _polled(buyer_feedback_sha256="b" * 64), adapter="coconala",
    )
    state = json.loads((root / "state.json").read_text())
    assert state["work_state"] == "WORK_REQUIRED"
    assert state["next_action"] == "WORK_REQUIRED"
    assert state["buyer_visible"] is False


def test_the_same_buyer_fact_seen_again_does_not_move_a_delivered_order(tmp_path):
    root = _delivered_awaiting_buyer(tmp_path, handled="b" * 64)
    delivery_project.record_queue_selection(
        tmp_path, _polled(buyer_feedback_sha256="b" * 64), adapter="coconala",
    )
    state = json.loads((root / "state.json").read_text())
    assert state["work_state"] == "DELIVERED"
    assert state["next_action"] == "await_buyer_decision"


def test_a_project_with_no_buyer_wait_recorded_is_still_refreshed(tmp_path):
    """Nothing durable to protect means the poll writes the decision as before."""
    root = delivery_project.record_queue_selection(
        tmp_path, {"request_id": "req-new", "buyer": "Buyer"}, adapter="coconala",
    )
    delivery_project.project_ledger.append(
        root, {"next_action": "retry_buyer_visible_delivery"}, "mid_flight",
    )
    delivery_project.record_queue_selection(tmp_path, _polled("req-new"), adapter="coconala")
    state = json.loads((root / "state.json").read_text())
    assert state["work_state"] == "WORK_REQUIRED"
    assert state["next_action"] == "WORK_REQUIRED"


def test_a_new_project_still_records_the_work_required_decision(tmp_path):
    root = delivery_project.record_queue_selection(
        tmp_path, _polled("req-fresh"), adapter="coconala",
    )
    state = json.loads((root / "state.json").read_text())
    assert state["work_state"] == "WORK_REQUIRED"
    assert state["next_action"] == "WORK_REQUIRED"


def test_nothing_to_send_plus_a_parked_buyer_decision_neither_builds_nor_resends(tmp_path):
    root = _delivered_awaiting_buyer(tmp_path)
    delivery_project.project_ledger.append(root, {"open_buyer_decisions": [
        {"item": "button size", "status": "awaiting_buyer_executive_decision"},
    ]}, "buyer_decision_opened")
    item = _polled(delivery_action="none")
    assert delivery_project.resolve_workflow_action(root, item) == "await_buyer"
    # ...and a work_required verdict still outranks it.
    assert delivery_project.resolve_workflow_action(root, _polled()) == "act"


def test_new_pending_feedback_overrides_a_parked_buyer_decision(tmp_path):
    root = _delivered_awaiting_buyer(tmp_path)
    delivery_project.project_ledger.append(root, {"open_buyer_decisions": [
        {"item": "button size", "status": "awaiting_buyer_executive_decision"},
    ]}, "buyer_decision_opened")
    item = _polled(
        delivery_action="none",
        buyer_feedback_sha256="b" * 64,
    )

    assert delivery_project.resolve_workflow_action(root, item) == "act"
