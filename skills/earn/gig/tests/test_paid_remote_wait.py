from __future__ import annotations

import hashlib
import importlib.util
import json
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load(name: str):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"{name}_wait_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")


def blocked_project(tmp_path: Path) -> tuple[Path, str, str]:
    root = tmp_path / "project"
    feedback = "a" * 64
    requirement = {"text": "Use the named provider and report the result.", "attachments": []}
    requirement_sha = hashlib.sha256(json.dumps(
        requirement, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    requirements_sha = hashlib.sha256(json.dumps(
        [requirement_sha], ensure_ascii=False, separators=(",", ":"),
    ).encode()).hexdigest()
    desired = {"provider_state": "awaiting_reply"}
    digest = hashlib.sha256(json.dumps(
        desired, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    semantic_contract = {
        "decision": "actionable",
        "mode": "remote",
        "feedback_sha256": feedback,
        "requirements_sha256": requirements_sha,
        "required_output": "Report the completed provider outcome.",
        "required_effect": "Wait for and process the provider response.",
        "required_assets": [],
    }
    semantic_sha = hashlib.sha256(json.dumps(
        semantic_contract, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    write_json(root / "requirements/live-buyer-reply.json", {
        "feedback_sha256": feedback,
        "accumulated_requirements": [{**requirement, "sha256": requirement_sha}],
        "accumulated_sha256": requirements_sha,
    })
    write_json(root / "delivery/paid-remote-intent.json", {
        "buyer_feedback_sha256": feedback,
        "requirements_sha256": requirements_sha,
        "target": "https://provider.example/status",
        "desired_state": desired,
        "desired_state_sha256": digest,
        "semantic_contract_sha256": semantic_sha,
    })
    write_json(root / "delivery/paid-remote-result.json", {
        "status": "blocked",
        "buyer_feedback_sha256": feedback,
        "requirements_sha256": requirements_sha,
        "target": "https://provider.example/status",
        "authenticated": True,
        "observed_state": desired,
        "after_state_digest": digest,
        "semantic_contract_sha256": semantic_sha,
        "blocker": "The provider has acknowledged the request but has not replied.",
        "business_outcome": {
            "required_effect_satisfied": False,
            "required_output_satisfied": False,
            "remaining_work": ["Wait for the provider reply."],
            "official_receipts": [{
                "provider": "provider.example",
                "kind": "inbox_thread_state",
                "url": "https://provider.example/status",
                "readback": "The request is acknowledged and no reply is present.",
            }],
        },
    })
    write_json(root / "context/paid-work-decision.json", semantic_contract)
    return root, feedback, digest


def test_current_blocked_remote_result_is_a_valid_wait(tmp_path):
    remote = load("paid_remote_result")
    root, feedback, digest = blocked_project(tmp_path)

    result = remote.validate_wait(root, feedback, digest, pass_start=0)

    assert result["status"] == "blocked"
    assert result["business_outcome"]["required_effect_satisfied"] is False


def test_completed_result_cannot_be_a_wait(tmp_path):
    remote = load("paid_remote_result")
    root, feedback, digest = blocked_project(tmp_path)
    result_path = root / "delivery/paid-remote-result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["status"] = "ok"
    write_json(result_path, result)

    with pytest.raises(ValueError, match="not an external wait"):
        remote.validate_wait(root, feedback, digest, pass_start=0)


def test_wait_accepts_supplementary_receipt_when_another_has_readback(tmp_path):
    remote = load("paid_remote_result")
    root, feedback, digest = blocked_project(tmp_path)
    result_path = root / "delivery/paid-remote-result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["business_outcome"]["official_receipts"].insert(0, {
        "provider": "provider.example",
        "kind": "completion_page",
        "url": "https://provider.example/thanks",
        "title": "Request received",
    })
    write_json(result_path, result)

    assert remote.validate_wait(root, feedback, digest, pass_start=0)["status"] == "blocked"


def test_wait_accepts_exact_readback_receipt_shape(tmp_path):
    remote = load("paid_remote_result")
    root, feedback, digest = blocked_project(tmp_path)
    result_path = root / "delivery/paid-remote-result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["business_outcome"]["official_receipts"] = [{
        "provider": "provider.example",
        "kind": "inbox_thread_state",
        "official_url": "https://provider.example/status",
        "readback_source": "provider API",
        "exact_readback": True,
    }]
    write_json(result_path, result)

    assert remote.validate_wait(root, feedback, digest, pass_start=0)["status"] == "blocked"


def test_paid_direct_maps_valid_blocked_owner_to_pending(tmp_path):
    paid = load("paid_direct")
    root, feedback, digest = blocked_project(tmp_path)

    assert paid._remote_owner_checkpoint(
        "blocked", root, feedback, digest, pass_start=0,
    ) == "pending"


def test_current_remote_wait_is_fresh(tmp_path):
    paid = load("paid_direct")
    root, feedback, digest = blocked_project(tmp_path)
    mtime = (root / "delivery/paid-remote-result.json").stat().st_mtime

    assert paid._remote_wait_is_fresh(root, feedback, digest, now=mtime + 10) is True


def test_remote_wait_expires_after_recheck_interval(tmp_path):
    paid = load("paid_direct")
    root, feedback, digest = blocked_project(tmp_path)
    mtime = (root / "delivery/paid-remote-result.json").stat().st_mtime

    assert paid._remote_wait_is_fresh(root, feedback, digest, now=mtime + 3601) is False


def test_future_dated_remote_wait_is_not_fresh(tmp_path):
    paid = load("paid_direct")
    root, feedback, digest = blocked_project(tmp_path)
    mtime = (root / "delivery/paid-remote-result.json").stat().st_mtime

    assert paid._remote_wait_is_fresh(root, feedback, digest, now=mtime - 1) is False


def test_current_wait_is_reused_before_semantic_decision(tmp_path):
    paid = load("paid_direct")
    root, feedback, _digest = blocked_project(tmp_path)

    assert paid._remote_wait_before_decision(
        root, {"buyer_feedback_sha256": feedback}, now=None,
    ) is True


def test_paid_project_executor_runs_one_owner_at_a_time():
    paid = load("paid_direct")
    active = 0
    maximum = 0
    lock = threading.Lock()

    def work():
        nonlocal active, maximum
        with lock:
            active += 1
            maximum = max(maximum, active)
        time.sleep(0.05)
        with lock:
            active -= 1

    with paid._paid_project_executor() as executor:
        futures = [executor.submit(work) for _ in range(2)]
        for future in futures:
            future.result()

    assert maximum == 1


def test_paid_admission_selects_one_project_and_rotates(tmp_path):
    paid = load("paid_direct")
    args = SimpleNamespace(projects_root=tmp_path)
    items = [
        {"talkroom_id": "101", "buyer": "buyer-a"},
        {"talkroom_id": "102", "buyer": "buyer-b"},
    ]

    first = paid._admitted_paid_projects(args, items)
    assert [item["talkroom_id"] for item in first] == ["101"]

    paid.delivery_project.record_queue_selection(tmp_path, first[0], adapter="coconala")
    second = paid._admitted_paid_projects(args, items)
    assert [item["talkroom_id"] for item in second] == ["102"]


def test_queued_paid_project_keeps_parent_pending():
    paid = load("paid_direct")
    rows = {
        "101": {"status": "completed"},
        "102": {"status": "queued"},
    }

    assert paid._paid_pending_count(rows) == 1
    assert paid._paid_parent_status(failed=0, pending=1) == "pending"
