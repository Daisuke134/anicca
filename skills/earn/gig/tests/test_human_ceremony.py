"""Contract tests for the bounded, provider-scoped human ceremony queue."""

from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "human_ceremony.py"
SCRIPTS = MODULE_PATH.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from provider_adapter import ProviderState


def _load_module():
    name = "gig_human_ceremony_test"
    spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ceremony = _load_module()


@pytest.fixture
def database(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    path = tmp_path / "connector-outbox.sqlite3"
    monkeypatch.setattr(ceremony, "DEFAULT_DATABASE", path)
    return path


def _state(provider: str = "upwork", **overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "provider": provider,
        "resource_id": "account-1",
        "action": "identity_verification",
        "state": "unverified",
        "observed_at": "2026-08-22T08:00:00+00:00",
        "evidence_hash": "a" * 64,
        "authorization_state": "approved_assisted",
        "provider_url": f"https://www.{provider}.com/verify/account-1",
        "deadline": "2026-08-23T08:00:00+00:00",
        "exact_act": {
            "instruction": "Open the identity check and capture the live selfie.",
            "control": "Start verification",
            "expected_result": "Identity status changes to verified",
        },
    }
    value.update(overrides)
    return value


def _state_predicate() -> dict[str, str]:
    return {"kind": "provider_state_changed", "expected_state": "verified"}


@pytest.mark.parametrize(
    "kind",
    ["identity", "financial", "physical_capture", "client_reserved"],
)
def test_only_declared_ceremony_kinds_create_bounded_durable_records(
    database: Path, kind: str,
):
    row = ceremony.request_ceremony(kind, _state(), _state_predicate())

    assert row.kind.value == kind
    assert row.status == "pending"
    assert row.provider_url == "https://www.upwork.com/verify/account-1"
    assert row.control == "Start verification"
    assert row.expected_result == "Identity status changes to verified"
    with sqlite3.connect(database) as connection:
        stored = connection.execute(
            "SELECT COUNT(*) FROM human_ceremonies WHERE provider='upwork'"
        ).fetchone()[0]
    assert stored == 1


def test_vague_request_and_missing_resume_evidence_are_rejected(database: Path):
    vague = _state(exact_act={
        "instruction": "Help", "control": "Click", "expected_result": "Done",
    })
    with pytest.raises(ValueError, match="exact_act"):
        ceremony.request_ceremony("identity", vague, _state_predicate())
    with pytest.raises(ValueError, match="resume_predicate"):
        ceremony.request_ceremony(
            "identity", _state(), {"kind": "provider_state_changed"}
        )


@pytest.mark.parametrize("authorization_state", ["approved_api", "approved_browser"])
def test_agent_executable_authorized_task_is_rejected(
    database: Path, authorization_state: str,
):
    with pytest.raises(ceremony.CeremonyRejected, match="agent_executable"):
        ceremony.request_ceremony(
            "identity",
            _state(authorization_state=authorization_state),
            _state_predicate(),
        )


def test_pending_ceremony_blocks_only_its_provider_lane(database: Path):
    ceremony.request_ceremony("identity", _state("upwork"), _state_predicate())

    assert ceremony.provider_runnable("upwork") is False
    assert ceremony.provider_runnable("fiverr") is True


def test_completion_requires_authoritative_changed_provider_state(database: Path):
    request = ceremony.request_ceremony("identity", _state(), _state_predicate())

    unchanged = ProviderState(
        provider="upwork", resource_id="account-1", action="identity_verification",
        state="unverified", observed_at="2026-08-22T09:00:00+00:00",
        evidence_hash="b" * 64,
    )
    with pytest.raises(ceremony.CeremonyRejected, match="provider_state_not_changed"):
        ceremony.complete_ceremony(request.ceremony_id, unchanged)
    with pytest.raises(ceremony.CeremonyRejected, match="stale_provider_evidence"):
        ceremony.complete_ceremony(request.ceremony_id, ProviderState(
            provider="upwork", resource_id="account-1", action="identity_verification",
            state="verified", observed_at="2026-08-22T07:00:00+00:00",
            evidence_hash="b" * 64,
        ))

    completed = ceremony.complete_ceremony(request.ceremony_id, ProviderState(
        provider="upwork", resource_id="account-1", action="identity_verification",
        state="verified", observed_at="2026-08-22T09:00:00+00:00",
        evidence_hash="b" * 64,
    ))
    assert completed.status == "completed"
    assert ceremony.provider_runnable("upwork") is True


def test_artifact_completion_requires_bound_kind_and_sha256(database: Path):
    request = ceremony.request_ceremony(
        "physical_capture",
        _state(action="capture_liveness"),
        {"kind": "artifact_hash", "artifact_kind": "liveness_receipt"},
    )

    with pytest.raises(ceremony.CeremonyRejected, match="artifact_kind_mismatch"):
        ceremony.complete_ceremony(request.ceremony_id, {
            "artifact_kind": "other", "artifact_hash": "c" * 64,
            "observed_at": "2026-08-22T09:00:00+00:00",
        })
    with pytest.raises(ValueError, match="artifact_hash"):
        ceremony.complete_ceremony(request.ceremony_id, {
            "artifact_kind": "liveness_receipt", "artifact_hash": "not-a-hash",
            "observed_at": "2026-08-22T09:00:00+00:00",
        })

    completed = ceremony.complete_ceremony(request.ceremony_id, {
        "artifact_kind": "liveness_receipt", "artifact_hash": "c" * 64,
        "observed_at": "2026-08-22T09:00:00+00:00",
    })
    assert completed.status == "completed"
    assert completed.completion_hash == "c" * 64
