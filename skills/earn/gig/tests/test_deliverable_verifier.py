from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import deliverable_verifier as verifier  # noqa: E402
from test_workflow_executor import NOW, _runner, _workspace  # noqa: E402
import workflow_executor  # noqa: E402


def _completed(tmp_path: Path, monkeypatch):
    root, revision, skills = _workspace(tmp_path)
    runner, counter = _runner(tmp_path / "builder.py"), tmp_path / "builder-count"
    monkeypatch.setenv("FAKE_RUNNER_COUNTER", str(counter))
    receipt = workflow_executor.execute_workflow(
        workspace=root, revision_sha256=revision, skills_root=skills,
        agent_runner=runner, timeout_seconds=60, now=NOW,
    )
    return root, receipt


def _review(**changes):
    value = {
        "verdict": "PASS",
        "reason": "The produced artifact satisfies the exact contract scope.",
        "criteria": [{
            "clause": "Build one tested local REST API integration artifact.",
            "status": "PASS",
            "evidence": "The artifact contains the completed integration output.",
        }],
        "factual_claims": [],
    }
    value.update(changes)
    return value


def test_pass_is_bound_to_contract_artifact_and_independent_context(tmp_path, monkeypatch):
    root, receipt = _completed(tmp_path, monkeypatch)
    result = verifier.verify_deliverables(
        workspace=root, execution_receipt=receipt, reviewer_context_id="fresh-review-1",
        review=_review(),
    )
    assert result["status"] == "PASS"
    assert result["delivery_intent_permitted"] is True
    assert result["artifact_sha256"] == [receipt["artifacts"][0]["sha256"]]
    assert result["contract_clause"] == "Build one tested local REST API integration artifact."


@pytest.mark.parametrize(
    "fault,expected",
    [
        ("self", "self_approval_rejected"),
        ("hash", "artifact_hash_mismatch"),
        ("criterion", "contract_criterion_missing"),
        ("claim", "unsupported_factual_claim"),
        ("private", "private_data_leak"),
    ],
)
def test_deterministic_gates_never_permit_delivery(tmp_path, monkeypatch, fault, expected):
    root, receipt = _completed(tmp_path, monkeypatch)
    context = "fresh-review-1"
    review = _review()
    if fault == "self":
        context = receipt["execution_id"]
    elif fault == "hash":
        receipt = json.loads(json.dumps(receipt))
        receipt["artifacts"][0]["sha256"] = "f" * 64
    elif fault == "criterion":
        review["criteria"] = []
    elif fault == "claim":
        review["factual_claims"] = [{"claim": "The API is 99.99% available.", "evidence": []}]
    else:
        artifact = root / receipt["artifacts"][0]["path"]
        artifact.write_text("customer email: private@example.com", encoding="utf-8")
        receipt["artifacts"][0]["sha256"] = verifier._sha_file(artifact)
        receipt["artifacts"][0]["bytes"] = artifact.stat().st_size

    result = verifier.verify_deliverables(
        workspace=root, execution_receipt=receipt, reviewer_context_id=context, review=review,
    )
    assert result["status"] in {"REVISE", "BLOCKED"}
    assert expected in result["evidence"]
    assert result["delivery_intent_permitted"] is False
