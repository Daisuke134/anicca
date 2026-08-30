from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import threading
import time
import zipfile
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


def test_concurrent_talkroom_history_persistence_does_not_duplicate_rows(tmp_path):
    queue = load("coconala_queue_snapshot")
    talkroom = {
        "history_complete": True,
        "messages": [{"message_id": "m1", "side": "buyer", "text": "hello",
                      "sent_at": None, "attachments": []}],
    }
    barrier = threading.Barrier(2)

    def persist():
        barrier.wait()
        queue.persist_talkroom_history(
            talkroom, "18214856", tmp_path, "18214856", "2026-08-30T00:00:00Z")

    workers = [threading.Thread(target=persist) for _ in range(2)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()

    ledger = tmp_path / "18214856/source/talkroom/messages.jsonl"
    assert len(ledger.read_text(encoding="utf-8").splitlines()) == 1


def test_paid_reader_retries_legacy_partial_talkroom_append(tmp_path):
    paid = load("paid_direct")
    root = tmp_path / "18214856"
    ledger = root / "source/talkroom/messages.jsonl"
    ledger.parent.mkdir(parents=True)
    row = {
        "version": 1, "source": "coconala_live_talkroom", "talkroom_id": "18214856",
        "message_id": "m1", "observed_at": "2026-08-30T00:00:00Z",
        "content_sha256": "0" * 64, "side": "buyer", "sent_at": None,
        "text": "hello", "attachments": [],
    }
    encoded = json.dumps(row, separators=(",", ":")) + "\n"
    ledger.write_text(encoded[:100], encoding="utf-8")
    write_json(root / "state.json", {"talkroom_id": "18214856"})

    def finish_legacy_write():
        time.sleep(0.02)
        with ledger.open("a", encoding="utf-8") as handle:
            handle.write(encoded[100:])

    writer = threading.Thread(target=finish_legacy_write)
    writer.start()
    rows = paid._official_message_rows(root, "18214856")
    writer.join()

    assert rows[0]["message_id"] == "m1"


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


def test_review_ready_acceptance_routes_to_progress_not_formal(tmp_path):
    cadence = load("delivery_cadence")
    queue = load("delivery_queue")
    artifact = tmp_path / "draft-v1.wav"
    artifact.write_bytes(b"review draft")
    acceptance = tmp_path / "acceptance.json"
    write_json(acceptance, {"status": "REVIEW_READY"})
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    item = {"talkroom_id": "123", "buyer_feedback_stage": "initial_request"}
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    write_json(queue.evidence_path(evidence_root, item), {
        "status": "REVIEW_READY",
        "project_root": str(tmp_path),
        "artifact_path": str(artifact),
        "artifact_version": "v1",
        "acceptance_status": "REVIEW_READY",
        "acceptance_evidence_path": str(acceptance),
        "package_sha256": digest,
    })

    evidence, blockers = queue.delivery_gate(item, evidence_root, tmp_path / "projects")
    decision = cadence.delivery_decision({**item, **evidence, "blockers": blockers})

    assert "missing_acceptance_evidence" not in blockers
    assert decision["mode"] == "progress"
    assert decision["formal_delivery_checkbox"] is False


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


def test_remote_owner_prompt_reconciles_project_effect_receipts_before_mutation(tmp_path):
    paid = load("paid_direct")
    root, feedback, _digest = blocked_project(tmp_path)
    requirements_sha = paid.paid_remote_result.requirements_digest(root, feedback)

    prompt = paid._repair_prompt(
        root, tmp_path / "item.json", feedback, requirements_sha,
        False, tmp_path / "cdp.py",
    )

    assert "project-owned external-effect receipts" in prompt
    assert "official provider and matching bookkeeping readback" in prompt
    assert "Never repeat an effect whose receipt is already verified" in prompt


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


def test_newer_exact_cycle_operator_policy_invalidates_remote_wait(tmp_path):
    paid = load("paid_direct")
    root, feedback, _digest = blocked_project(tmp_path)
    requirements_sha = paid.paid_remote_result.requirements_digest(root, feedback)
    result = root / "delivery/paid-remote-result.json"
    policy = root / "context/paid-file-operator-policy.json"
    write_json(policy, {
        "version": 1,
        "authorized_by": "account_owner",
        "request_id": root.name,
        "buyer_feedback_sha256": feedback,
        "requirements_sha256": requirements_sha,
        "directives": ["Reconcile newly verified project evidence."],
    })
    policy.touch()
    result.touch()
    policy.touch()

    assert paid._remote_wait_before_decision(
        root, {"buyer_feedback_sha256": feedback}, now=None,
    ) is False


def test_newer_operator_policy_invalidates_reported_answer_checkpoint(tmp_path):
    paid = load("paid_direct")
    root, feedback, _digest = blocked_project(tmp_path)
    answer = root / "delivery" / "paid-answer.json"
    write_json(answer, {"status": "answer", "message": "old result"})
    requirements_sha = paid.paid_remote_result.requirements_digest(root, feedback)
    policy = root / "context" / "paid-file-operator-policy.json"
    write_json(policy, {"version": 1, "authorized_by": "account_owner",
        "request_id": root.name, "buyer_feedback_sha256": feedback,
        "requirements_sha256": requirements_sha, "directives": ["Continue external work."]})
    answer.touch(); policy.touch()

    assert paid._operator_policy_newer_than(
        root, {"buyer_feedback_sha256": feedback}, answer,
    ) is True


def test_normalizer_restores_feedback_alias_and_canonical_digest(tmp_path):
    paid = load("paid_direct")
    root, feedback, _digest = blocked_project(tmp_path)
    intent_path = root / "delivery/paid-remote-intent.json"
    result_path = root / "delivery/paid-remote-result.json"
    intent = json.loads(intent_path.read_text())
    result = json.loads(result_path.read_text())
    intent.pop("buyer_feedback_sha256")
    result.pop("buyer_feedback_sha256")
    intent["feedback_sha256"] = feedback
    result["feedback_sha256"] = feedback
    after = root / "evidence/agent-PAID_REMOTE_OWNER/after.json"
    write_json(after, {
        "authenticated": True,
        "target": intent["target"],
        "observed_state": intent["desired_state"],
    })
    result["after_evidence"] = str(after.relative_to(root))
    for record in (intent, result):
        for key in ("desired_state_sha256", "desired_digest", "after_state_digest", "observed_digest"):
            if key in record:
                record[key] = "0" * 64
    write_json(intent_path, intent)
    write_json(result_path, result)

    paid._normalize_builder_result(root)

    intent = json.loads(intent_path.read_text())
    result = json.loads(result_path.read_text())
    digest = paid.paid_remote_result._sha(intent["desired_state"])
    assert intent["buyer_feedback_sha256"] == feedback
    assert result["buyer_feedback_sha256"] == feedback
    assert intent["desired_state_sha256"] == intent["desired_digest"] == digest
    assert result["desired_state_sha256"] == result["desired_digest"] == digest
    assert result["after_state_digest"] == result["observed_digest"] == digest


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


def test_answer_receipt_does_not_close_pending_buyer_artifact():
    paid = load("paid_direct")

    assert paid._answer_cycle_may_close({
        "buyer_feedback_pending_artifact": True,
        "buyer_visible_artifact_observed": False,
    }) is False
    assert paid._answer_cycle_may_close({
        "buyer_feedback_pending_artifact": False,
        "buyer_visible_artifact_observed": False,
    }) is True


def test_successful_external_artifact_receipt_is_reverified():
    paid = load("paid_direct")
    instruction = paid._owner_tool_result_instruction()

    assert "status=success" in instruction
    assert "independently verify every declared artifact and acceptance hash" in instruction
    assert "commercial-use evidence" in instruction
    assert "not an automatic approval" in instruction


def test_resumed_file_owner_refreshes_controller_tool_results(tmp_path):
    paid = load("paid_direct")
    root, staging = tmp_path / "root", tmp_path / "staging"
    (root / "context").mkdir(parents=True)
    (staging / "context").mkdir(parents=True)
    artifact = root / "delivery" / "artifact.zip"
    acceptance = root / "acceptance" / "acceptance.json"
    rights = root / "evidence" / "rights.json"
    for path, content in ((artifact, b"zip"), (acceptance, b"accept"), (rights, b"rights")):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    success = {
        "status": "success",
        "artifact": {"path": str(artifact), "sha256": hashlib.sha256(b"zip").hexdigest()},
        "acceptance": {"path": str(acceptance), "sha256": hashlib.sha256(b"accept").hexdigest()},
        "rights_and_correspondence": {
            "path": str(rights), "sha256": hashlib.sha256(b"rights").hexdigest(),
        },
    }
    (root / "context" / "paid-tool-results.json").write_text(json.dumps(success))
    (staging / "context" / "paid-tool-results.json").write_text('{"status":"failed"}')

    paid._refresh_owner_controller_context(root, staging)

    refreshed = json.loads((staging / "context" / "paid-tool-results.json").read_text())
    for field in ("artifact", "acceptance", "rights_and_correspondence"):
        copied = Path(refreshed[field]["path"])
        assert copied.is_file()
        copied.relative_to(staging)


def test_empty_tool_request_cannot_overwrite_success_receipt(tmp_path):
    paid = load("paid_direct")
    staging, root = tmp_path / "staging", tmp_path / "root"
    (staging / "delivery").mkdir(parents=True)
    (root / "context").mkdir(parents=True)
    (staging / "delivery" / "paid-tool-requests.json").write_text(
        '{"version":1,"requests":[]}'
    )
    (staging / "delivery" / "paid-tool-results.json").write_text(
        '{"version":1,"results":[]}'
    )
    success = '{"version":1,"status":"success"}'
    (root / "context" / "paid-tool-results.json").write_text(success)

    paid._persist_owner_tool_failure(staging, root)

    assert (root / "context" / "paid-tool-results.json").read_text() == success


def test_empty_tool_request_is_consumed_as_no_request(tmp_path):
    paid = load("paid_direct")
    (tmp_path / "delivery").mkdir()
    request = tmp_path / "delivery" / "paid-tool-requests.json"
    request.write_text('{"version":1,"requests":[]}')

    assert paid._execute_owner_tool_requests(tmp_path, tmp_path) == 0
    assert not request.exists()


def test_fresh_owner_staging_tolerates_precreated_context_directory(tmp_path):
    paid = load("paid_direct")
    root, staging = tmp_path / "root", tmp_path / "staging"
    for name in ("requirements", "source", "context"):
        (root / name).mkdir(parents=True)
    (root / "context" / "current.json").write_text("{}")
    (root / "state.json").write_text("{}")
    (staging / "context").mkdir(parents=True)

    paid._prepare_file_owner_staging(root, root / "context" / "current.json", staging)

    assert (staging / "context" / "current.json").is_file()


def test_single_member_archive_uses_its_actual_utf8_name(tmp_path):
    paid = load("paid_direct")
    archive = tmp_path / "review.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("硝子色の恋_review_v3.mp3", b"audio")

    name, data = paid._archive_member_data(archive, "硝子色の恋_review_v1.mp3")

    assert name == "硝子色の恋_review_v3.mp3"
    assert data == b"audio"


def test_repair_finding_only_applies_to_rejected_artifact_hash():
    paid = load("paid_direct")
    state = {
        "state": "REPAIR_PENDING",
        "mode": "file",
        "artifact_sha256": "a" * 64,
    }

    assert paid._repair_finding_applies(state, "a" * 64) is True
    assert paid._repair_finding_applies(state, "b" * 64) is False


def test_paid_preflight_uses_one_shared_browser_lock(tmp_path, monkeypatch):
    paid = load("paid_direct")
    called = []
    monkeypatch.setattr(paid, "_run", lambda command, step: called.append((command, step)) or "ok")
    args = SimpleNamespace(cdp_lock_dir=tmp_path / ".cdp-gig.lock")

    assert paid._run_paid_preflight(args, ["collector"]) == "ok"
    assert called == [(["collector"], "remote_resume")]
    assert (tmp_path / ".paid-preflight-browser.lock").is_file()


def test_effect_process_diagnostic_keeps_returncode_and_bounded_output():
    paid = load("paid_direct")
    process = SimpleNamespace(returncode=-9, stdout="out", stderr="err")

    assert paid._effect_process_diagnostic(process) == {
        "returncode": -9,
        "stdout_tail": "out",
        "stderr_tail": "err",
    }


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
    assert paid._shipment_basis_authorized("max_review_iterations_review_ready", "undeterminable")
    assert not paid._shipment_basis_authorized("max_review_iterations_review_ready", "needs_revision")


def test_paid_runner_contract_matches_runtime_terra_route():
    paid = load("paid_direct")

    assert paid.PAID_DECISION_MODEL == "gpt-5.6-terra"
    assert paid.PAID_FILE_MODEL == "gpt-5.6-terra"
    assert ("codex", "gpt-5.6-terra") in paid.PAID_RUNNER_CANDIDATES


def test_normalize_acceptance_repairs_archive_member_bookkeeping(tmp_path):
    paid = load("paid_direct")
    root = tmp_path / "project"
    (root / "delivery").mkdir(parents=True)
    (root / "acceptance").mkdir()
    (root / "context").mkdir()
    write_json(root / "context" / "paid-work-decision.json", {"required_assets": []})
    member = b"member audio"
    archive = root / "delivery" / "draft-v1.zip"
    import zipfile
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("draft-v1.wav", member)
    acceptance = root / "acceptance" / "acceptance-v1.json"
    write_json(acceptance, {"status": "REVIEW_READY", "acceptance_delta": ["review"]})
    write_json(root / "delivery" / "paid-work-result.json", {
        "status": "REVIEW_READY",
        "artifact_path": str(archive),
        "acceptance_evidence_path": str(acceptance),
        "acceptance_status": "REVIEW_READY",
        "acceptance_delta": ["review"],
        "required_assets": [],
        "artifact_assets": [{
            "asset_id": "draft", "path": str(archive), "archive_member": "draft-v1.wav",
            "bytes": archive.stat().st_size, "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "mime_type": "application/zip", "provenance": {"kind": "builder"},
        }],
    })

    paid._normalize_acceptance_delta(root)
    asset = json.loads((root / "delivery" / "paid-work-result.json").read_text())["artifact_assets"][0]

    assert asset["bytes"] == len(member)
    assert asset["sha256"] == hashlib.sha256(member).hexdigest()
    assert asset["mime_type"] in {"audio/wav", "audio/x-wav"}
    assert isinstance(asset["provenance"], str)


def test_run_bounded_does_not_wait_for_grandchild_inherited_pipe():
    paid = load("paid_direct")
    started = time.monotonic()

    result = paid._run_bounded([
        sys.executable, "-c",
        "import subprocess; subprocess.Popen(['sleep', '1.5']); print('done')",
    ], timeout=1)

    assert result.returncode == 0
    assert result.stdout.strip() == "done"
    assert time.monotonic() - started < 1


def test_runner_loop_id_uses_managed_control_plane_identity(monkeypatch):
    paid = load("paid_direct")
    monkeypatch.setenv("LIFE_MANAGER_LOOP_ID", "hf-gig-paid-direct")
    assert paid._runner_loop_id() == "hf-gig-paid-direct"


def test_remote_owner_cannot_treat_one_invalid_candidate_as_exhaustion():
    source = (SCRIPTS / "paid_direct.py").read_text(encoding="utf-8")
    assert "One invalid, private, unreachable, or unverified candidate is not batch exhaustion" in source
    assert "Do not finalize a partial batch after a command timeout or interruption" in source
    assert "A classification revision preserves the prior effect's semantic_contract_sha256" in source


def test_normalize_acceptance_absolutizes_project_relative_asset_path(tmp_path):
    paid = load("paid_direct")
    root = tmp_path / "project"
    (root / "delivery").mkdir(parents=True)
    (root / "acceptance").mkdir(); (root / "context").mkdir()
    archive = root / "delivery" / "draft-v1.zip"; archive.write_bytes(b"zip")
    acceptance = root / "acceptance" / "acceptance-v1.json"
    write_json(acceptance, {"status": "PASS", "acceptance_delta": ["ready"]})
    assets = [{"asset_id": "draft", "kind": "linked_asset", "minimum_count": 1,
               "buyer_visible_purpose": "download", "source_authority": "builder",
               "archive_required": True}]
    write_json(root / "context" / "paid-work-decision.json", {"required_assets": assets})
    write_json(root / "delivery" / "paid-work-result.json", {
        "status": "ok", "artifact_path": str(archive),
        "acceptance_evidence_path": str(acceptance), "acceptance_status": "PASS",
        "acceptance_delta": ["ready"], "required_assets": assets,
        "artifact_assets": [{"asset_id": "draft", "path": "delivery/draft-v1.zip",
            "bytes": 3, "sha256": hashlib.sha256(b"zip").hexdigest(),
            "mime_type": "application/zip", "provenance": "builder"}],
    })

    paid._normalize_acceptance_delta(root)
    asset = json.loads((root / "delivery" / "paid-work-result.json").read_text())["artifact_assets"][0]
    assert asset["path"] == str(archive.resolve())
