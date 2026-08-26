from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest


GIG = Path(__file__).resolve().parents[1]
SCRIPTS, PROVIDERS = GIG / "scripts", GIG / "scripts" / "providers"
for directory in (SCRIPTS, PROVIDERS):
    sys.path.insert(0, str(directory))

from upwork_revision import RevisionError, process_revision  # noqa: E402


def _inputs(tmp_path: Path, **changes):
    root = tmp_path / "contract-1"
    artifact = root / "artifacts" / "revisions" / "execution-1" / "result.txt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("original delivery", encoding="utf-8")
    state = root / "state.json"
    if not state.exists():
        state.write_text(json.dumps({"request_id": "contract-1", "adapter": "upwork",
                                     "next_action": "await_client"}) + "\n", encoding="utf-8")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    contract = {
        "contract_id": "contract-1", "milestone_id": "milestone-1",
        "scope": "Repair authentication for the documented Neuroflow API endpoint.",
        "deadline": "2026-09-01", "contract_sha256": "a" * 64,
    }
    request = {
        "provider": "upwork", "message_id": "message-9", "room_id": "room-2",
        "contract_id": "contract-1", "milestone_id": "milestone-1",
        "request_text": "Please handle the documented 401 response in the same endpoint.",
        "requested_deadline": None, "observed_at": "2026-08-23T05:00:00+00:00",
        "evidence_sha256": "b" * 64,
    }
    decision = {
        "in_scope": True, "scope_clause": contract["scope"],
        "reason_codes": ["same_endpoint_correction"], "evidence_sha256": "c" * 64,
    }
    execution = {
        "execution_id": "d" * 64, "contract_sha256": contract["contract_sha256"],
        "artifacts": [{"path": str(artifact.relative_to(root)), "sha256": digest,
                       "bytes": len(b"original delivery")}],
    }
    request.update(changes.pop("request", {})); decision.update(changes.pop("decision", {}))
    contract.update(changes.pop("contract", {}))
    assert not changes
    return root, contract, request, decision, execution


def _run(tmp_path: Path, **changes):
    root, contract, request, decision, execution = _inputs(tmp_path, **changes)
    result = process_revision(
        workspace=root, contract=contract, request=request, decision=decision,
        prior_execution=execution, elapsed_seconds=12, model_cost_usd_minor=3,
        tool_cost_usd_minor=2,
    )
    return root, result


def test_duplicate_official_request_routes_once_and_records_one_economic_fact(tmp_path):
    root, first = _run(tmp_path)
    _, replay = _run(tmp_path)

    assert replay == first
    assert first["route"] == "fulfillment"
    assert first["next_actions"] == [
        "execute_workflow", "verify_deliverables", "deliver_milestone",
    ]
    facts = [json.loads(line) for line in (root / "events.jsonl").read_text().splitlines()
             if json.loads(line).get("event") == "economic_fact"]
    assert len(facts) == 1
    assert json.loads((root / "state.json").read_text())["next_action"] == "execute_workflow"
    assert len(list((root / "requirements" / "client-revisions").glob("*.json"))) == 1


@pytest.mark.parametrize("fault", ["out_of_scope", "changed_deadline"])
def test_scope_or_deadline_change_returns_to_negotiation_without_fulfillment(tmp_path, fault):
    changes = (
        {"decision": {"in_scope": False, "reason_codes": ["new_endpoint"]}}
        if fault == "out_of_scope"
        else {"request": {"requested_deadline": "2026-08-25"}}
    )
    root, result = _run(tmp_path, **changes)

    assert result["route"] == "negotiation"
    assert result["next_actions"] == ["negotiate_scope_change"]
    assert json.loads((root / "state.json").read_text())["next_action"] == "negotiate_scope_change"
    assert not (root / "requirements" / "client-revisions").exists()


def test_overwritten_original_artifact_is_rejected_before_revision_state(tmp_path):
    root, contract, request, decision, execution = _inputs(tmp_path)
    (root / execution["artifacts"][0]["path"]).write_text("overwritten", encoding="utf-8")

    with pytest.raises(RevisionError, match="original_artifact_changed"):
        process_revision(
            workspace=root, contract=contract, request=request, decision=decision,
            prior_execution=execution, elapsed_seconds=12, model_cost_usd_minor=3,
            tool_cost_usd_minor=2,
        )
    assert not (root / "events.jsonl").exists()


def test_request_is_bound_to_exact_provider_message_and_milestone(tmp_path):
    root, result = _run(tmp_path)
    packet = json.loads(Path(result["revision_request"]).read_text())

    assert packet["source"] == {
        "provider": "upwork", "message_id": "message-9", "room_id": "room-2",
        "contract_id": "contract-1", "milestone_id": "milestone-1",
        "evidence_sha256": "b" * 64,
    }
    assert packet["prior_execution_id"] == "d" * 64


def test_same_message_identity_cannot_be_replayed_with_changed_request_text(tmp_path):
    _run(tmp_path)
    with pytest.raises(RevisionError, match="revision_identity_collision"):
        _run(tmp_path, request={"request_text": "Build a second unrelated endpoint."})
