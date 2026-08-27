from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


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


def test_business_outcome_accepts_provider_kind_result_as_official_source():
    paid = load("paid_direct")
    outcome = {
        "required_effect_satisfied": True,
        "required_output_satisfied": True,
        "remaining_work": [],
        "official_receipts": [{
            "effect_key": "gmail:reply:1",
            "official_url": "https://mail.google.com/mail/u/0/#inbox/thread",
            "provider": "Google Gmail",
            "kind": "authenticated_dom_readback",
            "result": "Exact sent message is visible in the official thread.",
            "exact_readback": True,
        }],
    }

    assert paid._validated_business_outcome({"business_outcome": outcome}) == outcome


def test_business_outcome_effect_match_ignores_descriptive_receipt_metadata():
    paid = load("paid_direct")
    builder = {
        "required_effect_satisfied": True,
        "required_output_satisfied": True,
        "remaining_work": [],
        "official_receipts": [{
            "effect_key": "gmail:reply:1",
            "official_url": "https://mail.google.com/mail/u/0/#inbox/thread",
            "provider": "Google Gmail",
            "kind": "authenticated_dom_readback",
            "result": "Exact sent message is visible.",
            "exact_readback": True,
        }],
    }
    verifier = {
        "required_effect_satisfied": True,
        "required_output_satisfied": True,
        "remaining_work": [],
        "official_receipts": [{
            "effect_key": "gmail:reply:1",
            "official_url": "https://mail.google.com/mail/u/0/#inbox/thread",
            "readback_source": "Authenticated Gmail DOM message node",
            "exact_readback": True,
        }],
    }

    assert paid._business_outcomes_match_effects(builder, verifier) is True


def test_formal_approval_survives_later_seller_acknowledgement(tmp_path):
    paid = load("paid_direct")
    root = tmp_path / "18130722"
    write_json(root / "state.json", {"talkroom_id": "18130722"})

    def row(side: str, message_id: str, text_value: str) -> dict:
        value = {
            "version": 1,
            "source": "coconala_live_talkroom",
            "talkroom_id": "18130722",
            "message_id": message_id,
            "observed_at": "2026-08-24T00:00:00Z",
            "side": side,
            "sent_at": None,
            "text": text_value,
            "attachments": [],
        }
        value["content_sha256"] = paid._official_content_sha256(value)
        return value

    buyer_row = row("buyer", "buyer-approved", "Approved; share the project and formally deliver.")
    seller_row = row("seller", "seller-ack", "Acknowledged; I will share it.")
    messages = root / "source/talkroom/messages.jsonl"
    messages.parent.mkdir(parents=True)
    messages.write_text(
        "\n".join(json.dumps(value, ensure_ascii=False) for value in (buyer_row, seller_row)) + "\n",
        encoding="utf-8",
    )
    latest = paid._latest_official_identity(root, "18130722")
    latest_buyer = paid._latest_official_buyer_identity(root, "18130722")
    decision = {
        "decision": "actionable",
        "mode": "file",
        "feedback_sha256": "a" * 64,
        "requirements_sha256": "b" * 64,
        "latest_message_identity": latest,
        "required_output": "Share the approved project package.",
        "required_effect": "Formally deliver after the share.",
        "required_assets": [{
            "asset_id": "project_package",
            "kind": "linked_asset",
            "minimum_count": 1,
            "buyer_visible_purpose": "Download the approved project package.",
            "source_authority": "builder",
            "archive_required": True,
        }],
        "delivery_stage": "formal",
        "formal_approval_evidence": latest_buyer,
        "unresolved": [],
    }

    assert latest["side"] == "seller"
    assert latest_buyer["side"] == "buyer"
    assert paid._validate_paid_decision(
        decision, "a" * 64, "b" * 64, latest, latest_buyer,
    ) == decision


def test_file_prepare_creates_missing_project_delivery_directory(tmp_path, monkeypatch):
    paid = load("paid_direct")
    root = tmp_path / "project"
    root.mkdir()
    monkeypatch.setattr(
        paid.paid_remote_result, "requirements_digest", lambda *_args: "a" * 64,
    )
    monkeypatch.setattr(
        paid.delivery_queue, "evidence_path", lambda *_args: tmp_path / "stable.json",
    )

    def observe_delivery(*_args):
        assert (root / "delivery").is_dir()
        raise RuntimeError("observed")

    monkeypatch.setattr(paid, "_validate_file_authorization", observe_delivery)

    with pytest.raises(RuntimeError, match="observed"):
        paid._prepare_file(
            SimpleNamespace(delivery_evidence_dir=tmp_path, projects_root=tmp_path),
            tmp_path / "item.json", root, {}, tmp_path / "base", "b" * 64,
        )


def test_prior_artifact_candidates_include_only_project_receipt_linked_zips(tmp_path):
    paid = load("paid_direct")
    root = tmp_path / "project"
    delivery_zip = root / "delivery" / "current.zip"
    receipt_zip = root / "deliverables" / "approved" / "final.zip"
    unrelated_zip = root / "deliverables" / "unrelated.zip"
    for path in (delivery_zip, receipt_zip, unrelated_zip):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(path.name.encode())
    write_json(root / "acceptance" / "upload-receipt.json", {
        "status": "uploaded", "artifact": str(receipt_zip),
    })

    assert paid._prior_artifact_candidates(root) == [delivery_zip, receipt_zip]


def test_formal_handoff_does_not_carry_superseded_complaints_forward():
    paid = load("paid_direct")

    instruction = paid._file_customer_message_instruction()

    assert "latest buyer-side message" in instruction
    assert "later explicit buyer approval supersedes" in instruction


def test_next_artifact_version_includes_receipt_linked_prior_candidates(tmp_path):
    paid = load("paid_direct")
    root = tmp_path / "project"
    (root / "delivery").mkdir(parents=True)
    write_json(root / "state.json", {"current_version": "v97"})
    prior = root / "prior" / "approved-v107-package.zip"
    prior.parent.mkdir()
    prior.write_bytes(b"zip")

    assert paid._next_artifact_version(root, [prior]) == "v108"


def test_delivery_cadence_accepts_oversize_linked_asset_and_latest_buyer_approval(tmp_path, monkeypatch):
    cadence = load("delivery_cadence")
    artifact = tmp_path / "package-v1.zip"
    artifact.write_bytes(b"linked package")
    acceptance = tmp_path / "acceptance.json"
    write_json(acceptance, {"status": "PASS"})
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    buyer = {"message_id": "buyer-approval", "content_sha256": "a" * 64, "side": "buyer"}
    seller = {"message_id": "seller-ack", "content_sha256": "b" * 64, "side": "seller"}
    monkeypatch.setattr(cadence, "MARKETPLACE_ARTIFACT_MAX_BYTES", 0)
    item = {
        "artifact_path": str(artifact), "artifact_version": "v1",
        "acceptance_status": "PASS", "acceptance_evidence_path": str(acceptance),
        "package_sha256": digest, "blockers": [],
        "required_assets": [{"asset_id": "package", "kind": "linked_asset", "minimum_count": 1}],
        "artifact_assets": [{"asset_id": "package", "type": "linked_asset", "path": str(artifact)}],
        "formal_approval_evidence": buyer,
        "latest_message_identity": seller,
        "latest_buyer_message_identity": buyer,
    }

    assert cadence._artifact_ready(item) is True
    assert cadence.delivery_decision(item)["mode"] == "formal"


def test_formal_browser_accepts_latest_buyer_approval_and_linked_asset():
    formal = load("coconala_formal_delivery_browser")
    buyer = {"message_id": "buyer-approval", "content_sha256": "a" * 64, "side": "buyer"}
    queue = {
        "formal_approval_evidence": buyer,
        "latest_message_identity": {
            "message_id": "seller-ack", "content_sha256": "b" * 64, "side": "seller",
        },
        "latest_buyer_message_identity": buyer,
        "delivery_evidence": {
            "required_assets": [{"asset_id": "package", "kind": "linked_asset", "minimum_count": 1}],
            "artifact_assets": [{"asset_id": "package", "type": "linked_asset"}],
        },
    }

    assert formal._formal_approval_ready(queue) is True
    assert formal._linked_asset_delivery(queue["delivery_evidence"]) is True


def test_paid_queue_accepts_completed_linked_formal_readback():
    evidence = load("paid_queue_evidence")
    linked = {
        "required_assets": [{"asset_id": "package", "kind": "linked_asset", "minimum_count": 1}],
        "artifact_assets": [{"asset_id": "package", "type": "linked_asset"}],
    }

    assert evidence._linked_asset_delivery(linked) is True
    assert evidence._formal_transaction_state_ready("取引完了") is True


def test_reported_formal_cycle_accepts_exact_linked_message_readback(tmp_path, monkeypatch):
    paid = load("paid_direct")
    projects = tmp_path / "projects"
    root = projects / "18130722"
    artifact = root / "delivery" / "package-v1.zip"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"package")
    message = "正式な納品とさせていただきます。"
    event = {
        "event": "FORMAL_DELIVERY_CONFIRMED", "project_id": "18130722",
        "talkroom_id": "18130722", "linked_asset_delivery": True,
        "seller_attachment_readback": None, "seller_message_readback": message,
        "artifact_path": str(artifact), "artifact_bytes": artifact.stat().st_size,
        "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
    }
    (root / "events.jsonl").write_text(json.dumps(event, ensure_ascii=False) + "\n")
    feedback = "c" * 64
    write_json(root / "state.json", {
        "formal_delivery_confirmed": True,
        "handled_buyer_feedback_sha256": feedback,
    })
    monkeypatch.setattr(paid.delivery_project, "resolve_project_root", lambda *_args: root)
    item = {
        "talkroom_id": "18130722", "formal_delivery_observed": False,
        "talkroom_state": "取引完了", "buyer_feedback_pending_artifact": True,
        "buyer_feedback_sha256": feedback,
        "seller_messages": [{"text": message, "attachments": []}],
    }

    assert paid._reported_formal_cycle(SimpleNamespace(projects_root=projects), item) == root


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


def test_remote_owner_prompt_includes_exact_cycle_account_owner_policy(tmp_path):
    paid = load("paid_direct")
    root, feedback, _digest = blocked_project(tmp_path)
    requirements_sha = paid.paid_remote_result.requirements_digest(root, feedback)
    directive = "Do not contact the buyer for another verification code; use an authorized reusable account."
    write_json(root / "context/paid-file-operator-policy.json", {
        "version": 1,
        "authorized_by": "account_owner",
        "request_id": root.name,
        "buyer_feedback_sha256": feedback,
        "requirements_sha256": requirements_sha,
        "directives": [directive],
    })

    prompt = paid._repair_prompt(
        root, tmp_path / "item.json", feedback, requirements_sha,
        False, tmp_path / "cdp.py",
    )

    assert directive in prompt
    assert "account-owner policy" in prompt


def test_remote_owner_prompt_searches_complete_repo_and_valid_shared_tools(tmp_path):
    paid = load("paid_direct")
    root, feedback, _digest = blocked_project(tmp_path)
    requirements_sha = paid.paid_remote_result.requirements_digest(root, feedback)

    prompt = paid._repair_prompt(
        root, tmp_path / "item.json", feedback, requirements_sha,
        False, tmp_path / "cdp.py",
    )

    assert f"search {paid.REPO_ROOT} with rg" in prompt
    assert str(paid.REPO_ROOT / "skills/_shared/resource_resolver.py") in prompt
    assert str(paid.REPO_ROOT / "skills/browser/with-browser.sh") in prompt


def test_decision_prompt_scopes_required_assets_to_current_bounded_output(tmp_path):
    paid = load("paid_direct")

    identity = {"message_id": "m1", "content_sha256": "d" * 64, "side": "buyer"}
    prompt = paid._decision_prompt(
        tmp_path / "context.json", "a" * 64, "b" * 64, "c" * 64,
        identity, identity,
    ).decode()

    assert "current bounded output" in prompt
    assert "future event" in prompt
    assert "Do not hide a required asset only in unresolved" not in prompt


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


def test_paid_project_executor_runs_different_owners_in_parallel():
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

    assert maximum == 2


def test_paid_effect_child_does_not_take_global_browser_lock(tmp_path):
    paid = load("paid_direct")
    args = SimpleNamespace(**{
        name: tmp_path / name for name in (
            "run_with_cdp_lock", "evidence_dir", "projects_root", "collector",
            "answer_browser", "formal_browser", "delivery_evidence_dir", "cdp_helper",
            "context_compiler", "dm_collector", "agent_runner", "runner_schema",
            "artifact_schema", "cdp_lock_dir",
        )
    }, today="2026-08-24")

    command = paid._effect_command(
        args, tmp_path / "item-18183618-prepared.json", tmp_path / "result.json",
    )

    assert command[0] == sys.executable
    assert "--write-item" in command
    assert str(args.run_with_cdp_lock) not in command


def test_paid_child_env_scopes_browser_owner_by_talkroom(tmp_path):
    paid = load("paid_direct")
    args = SimpleNamespace(cdp_lock_dir=tmp_path / "legacy-lock")

    env = paid._fresh_child_env(args, owner="paid-direct-18183618")

    assert env["CLOAK_BROWSER_OWNER"] == "paid-direct-18183618"
    assert "GIG_CDP_LOCK_HELD" not in env


def test_effect_process_diagnostic_is_bounded():
    paid = load("paid_direct")
    process = SimpleNamespace(returncode=75, stdout="x" * 2500, stderr="deferred_cdp_busy")

    diagnostic = paid._effect_process_diagnostic(process)

    assert diagnostic == {
        "returncode": 75,
        "stdout_tail": "x" * 2000,
        "stderr_tail": "deferred_cdp_busy",
    }


def test_paid_admission_selects_independent_projects_in_same_wake(tmp_path):
    paid = load("paid_direct")
    args = SimpleNamespace(projects_root=tmp_path)
    items = [
        {"talkroom_id": "101", "buyer": "buyer-a"},
        {"talkroom_id": "102", "buyer": "buyer-b"},
    ]

    admitted = paid._admitted_paid_projects(args, items)

    assert [item["talkroom_id"] for item in admitted] == ["101", "102"]


def test_paid_admission_skips_future_timed_retry_for_actionable_project(tmp_path):
    paid = load("paid_direct")
    args = SimpleNamespace(projects_root=tmp_path)
    items = [
        {"talkroom_id": "101", "buyer": "buyer-a"},
        {"talkroom_id": "102", "buyer": "buyer-b"},
    ]
    for item in items:
        root = tmp_path / item["talkroom_id"]
        root.mkdir(parents=True)
        write_json(root / "state.json", {"talkroom_id": item["talkroom_id"]})
    write_json(tmp_path / "101/context/paid-retry.json", {
        "version": 1,
        "status": "timed_retry",
        "retry_not_before": "2999-01-01T00:00:00+00:00",
        "reason": "provider_attempt_limit",
    })

    admitted = paid._admitted_paid_projects(args, items)

    assert [item["talkroom_id"] for item in admitted] == ["102"]


def test_paid_admission_orders_project_scoped_priority_without_excluding_others(tmp_path):
    paid = load("paid_direct")
    args = SimpleNamespace(projects_root=tmp_path)
    items = [
        {"talkroom_id": "101", "buyer": "buyer-a", "delivery_date": "2026-08-01"},
        {"talkroom_id": "102", "buyer": "buyer-b", "delivery_date": "2026-08-31"},
    ]
    for item in items:
        root = tmp_path / item["talkroom_id"]
        root.mkdir(parents=True)
        write_json(root / "state.json", {"talkroom_id": item["talkroom_id"]})
    write_json(tmp_path / "102/context/paid-priority.json", {
        "version": 1,
        "priority": 0,
        "authorized_by": "account_owner",
        "reason": "current_paid_closure_cursor",
    })

    admitted = paid._admitted_paid_projects(args, items)

    assert [item["talkroom_id"] for item in admitted] == ["102", "101"]


def test_queued_paid_project_keeps_parent_pending():
    paid = load("paid_direct")
    rows = {
        "101": {"status": "completed"},
        "102": {"status": "queued"},
    }

    assert paid._paid_pending_count(rows) == 1
    assert paid._paid_parent_status(failed=0, pending=1) == "pending"


def test_review_ready_undeterminable_ships_only_at_final_review_round():
    paid = load("paid_direct")

    assert paid._review_ready_may_ship("undeterminable", True, paid.MAX_FILE_REVIEW_ITERATIONS)
    assert not paid._review_ready_may_ship("undeterminable", False, paid.MAX_FILE_REVIEW_ITERATIONS)
    assert not paid._review_ready_may_ship("semantic_refusal", True, paid.MAX_FILE_REVIEW_ITERATIONS)
    assert not paid._review_ready_may_ship("needs_revision", True, paid.MAX_FILE_REVIEW_ITERATIONS)
