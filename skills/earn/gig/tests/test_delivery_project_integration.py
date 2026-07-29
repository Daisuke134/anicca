import json
import os
import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import delivery_project


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


def test_missing_request_id_is_rejected(tmp_path):
    try:
        delivery_project.record_queue_selection(tmp_path, {"buyer": "Buyer"}, adapter="coconala")
    except ValueError as exc:
        assert "request_id" in str(exc)
    else:
        raise AssertionError("missing request_id must fail closed")


def test_direct_offer_falls_back_to_talkroom_and_preserves_existing_wait_state(tmp_path):
    root = delivery_project.record_queue_selection(tmp_path, {
        "contract_id": "direct-offer:6198868",
        "talkroom_id": "17943244",
        "buyer": "Buyer",
        "buyer_visible_artifact_observed": True,
        "buyer_feedback_pending_artifact": False,
        "buyer_agreement_observed": False,
        "talkroom_state": "取引中",
    }, adapter="coconala")
    assert root == tmp_path / "17943244"
    delivery_project.project_ledger.append(root, {
        "buyer_visible": True,
        "formal_delivery": False,
        "next_action": "await_buyer_approval_for_publication",
    }, "review_artifact_sent")

    root = delivery_project.record_queue_selection(tmp_path, {
        "contract_id": "direct-offer:6198868",
        "talkroom_id": "17943244",
        "buyer": "Buyer",
        "buyer_visible_artifact_observed": True,
        "buyer_feedback_pending_artifact": False,
        "buyer_agreement_observed": False,
        "talkroom_state": "取引中",
    }, adapter="coconala")
    state = json.loads((root / "state.json").read_text())
    assert state["request_id"] == "17943244"
    assert state["source_contract_id"] == "direct-offer:6198868"
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
