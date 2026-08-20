import hashlib
import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "writer_incident_queue.py"
SPEC = importlib.util.spec_from_file_location("writer_incident_queue", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_register_investigation_advances_claimed_incident_to_receipt_next_action(
    tmp_path: Path,
) -> None:
    fingerprint = "a" * 64
    lease_id = "lease-1"
    queue = {
        "schema": "writer.self-heal.incident-queue",
        "version": 1,
        "items": {
            fingerprint: {
                "fingerprint": fingerprint,
                "state": "CLAIMED",
                "lease_id": lease_id,
                "next_action": "RUNBOOK_OR_INVESTIGATE",
            }
        },
    }
    receipt_path = tmp_path / "investigation.json"
    receipt = {
        "schema": "writer.self-heal.unknown-investigation",
        "version": 1,
        "fingerprint": fingerprint,
        "cause_status": "EVIDENCE_BACKED_HYPOTHESIS",
        "next_action": "CHARACTERIZE_PREEXISTING_EFFECT_RECONCILIATION",
        "evidence_gaps": [],
    }
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    result = MODULE.register_investigation(
        queue,
        fingerprint,
        lease_id,
        receipt_path,
        "2026-08-06T19:10:00+09:00",
    )

    assert result["state"] == "CLAIMED"
    assert result["lease_id"] == lease_id
    assert result["next_action"] == "CHARACTERIZE_PREEXISTING_EFFECT_RECONCILIATION"
    assert result["investigation_receipt"] == {
        "path": str(receipt_path.resolve()),
        "sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        "cause_status": "EVIDENCE_BACKED_HYPOTHESIS",
    }
    assert result["investigated_at"] == "2026-08-06T19:10:00+09:00"


def test_register_characterization_advances_claimed_incident_to_candidate_fix(
    tmp_path: Path,
) -> None:
    fingerprint = "a" * 64
    lease_id = "lease-1"
    queue = {
        "schema": "writer.self-heal.incident-queue",
        "version": 1,
        "items": {
            fingerprint: {
                "fingerprint": fingerprint,
                "state": "CLAIMED",
                "lease_id": lease_id,
                "next_action": "CHARACTERIZE_PREEXISTING_EFFECT_RECONCILIATION",
            }
        },
    }
    receipt_path = tmp_path / "characterization.json"
    receipt = {
        "schema": "writer.self-heal.characterization-receipt",
        "version": 1,
        "status": "RED_VERIFIED",
        "fingerprint": fingerprint,
        "base_head": "b" * 40,
        "branch": "repair/writer-aaaaaaaaaaaa-characterization",
        "test_path": "skills/writer-agent/tests/test_characterization.py",
        "observed_exit_code": 1,
        "failure_signature": "captured-failure",
        "changed_paths": ["skills/writer-agent/tests/test_characterization.py"],
        "next_action": "GENERATE_CANDIDATE_FIX",
    }
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    result = MODULE.register_characterization(
        queue,
        fingerprint,
        lease_id,
        receipt_path,
        "2026-08-06T19:35:00+09:00",
    )

    assert result["state"] == "CLAIMED"
    assert result["lease_id"] == lease_id
    assert result["next_action"] == "GENERATE_CANDIDATE_FIX"
    assert result["characterization_receipt"] == {
        "path": str(receipt_path.resolve()),
        "sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        "status": "RED_VERIFIED",
        "test_path": "skills/writer-agent/tests/test_characterization.py",
        "test_sha256": None,
        "failure_signature": "captured-failure",
    }
    assert result["characterized_at"] == "2026-08-06T19:35:00+09:00"


def test_register_candidate_advances_claimed_incident_to_sensitive_verification(
    tmp_path: Path,
) -> None:
    fingerprint = "a" * 64
    lease_id = "lease-1"
    queue = {
        "schema": "writer.self-heal.incident-queue",
        "version": 1,
        "items": {
            fingerprint: {
                "fingerprint": fingerprint,
                "state": "CLAIMED",
                "lease_id": lease_id,
                "next_action": "GENERATE_CANDIDATE_FIX",
            }
        },
    }
    receipt_path = tmp_path / "candidate.json"
    receipt = {
        "schema": "writer.self-heal.candidate-verification-receipt",
        "version": 1,
        "status": "CANDIDATE_VERIFIED",
        "fingerprint": fingerprint,
        "feature_commit": "b" * 40,
        "artifacts": [{
            "path": "skills/writer-agent/scripts/publication-guard.py",
            "sha256": "c" * 64,
        }],
        "invariants": {
            "draft_is_public": False,
            "incident_resolved": False,
            "deployed": False,
        },
        "next_action": "VERIFY_SENSITIVE_REPAIR_IN_ISOLATED_FIXTURE",
    }
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    result = MODULE.register_candidate(
        queue,
        fingerprint,
        lease_id,
        receipt_path,
        "2026-08-06T19:47:00+09:00",
    )

    assert result["state"] == "CLAIMED"
    assert result["lease_id"] == lease_id
    assert result["next_action"] == "VERIFY_SENSITIVE_REPAIR_IN_ISOLATED_FIXTURE"
    assert result["candidate_receipt"] == {
        "path": str(receipt_path.resolve()),
        "sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        "status": "CANDIDATE_VERIFIED",
        "feature_commit": "b" * 40,
    }
    assert result["candidate_verified_at"] == "2026-08-06T19:47:00+09:00"
