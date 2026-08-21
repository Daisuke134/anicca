"""Receipt- and owner-gated recovery for stale Writer repair leases."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _module(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DISPATCH = _module("writer_repair_dispatch")
QUEUE = _module("writer_incident_queue")


def _queue(fingerprint: str, lease_id: str) -> dict:
    return {
        "schema": "writer.self-heal.incident-queue",
        "version": 1,
        "items": {
            fingerprint: {
                "fingerprint": fingerprint,
                "state": "CLAIMED",
                "lease_id": lease_id,
                "first_seen_at": "2026-08-21T00:00:00Z",
                "next_action": "RUNBOOK_OR_INVESTIGATE",
            }
        },
    }


def _attempt(path: Path, fingerprint: str, lease_id: str, *, route: str, status: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "schema": "writer.self-heal.repair-attempt",
        "version": 1,
        "fingerprint": fingerprint,
        "lease_id": lease_id,
        "route": route,
        "model": {"status": status},
    }))


def _decision(path: Path, fingerprint: str, lease_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "schema": "writer.self-heal.runbook-decision",
        "version": 1,
        "fingerprint": fingerprint,
        "lease_id": lease_id,
        "route": "KNOWN",
        "executed": False,
        "next_action": "EXECUTE_BOUNDED_RUNBOOK",
    }))


def _investigation(path: Path, fingerprint: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "schema": "writer.self-heal.unknown-investigation",
        "version": 1,
        "fingerprint": fingerprint,
    }))


def test_known_terminal_handoff_moves_to_wait_without_execution(tmp_path: Path, monkeypatch) -> None:
    state = tmp_path / "state"
    self_heal = state / "self-heal"
    fingerprint, lease = "a" * 64, "repair-known"
    queue = _queue(fingerprint, lease)
    attempt = self_heal / "repair-attempts" / f"{fingerprint}-{lease}.json"
    decision = self_heal / "runbook-decisions" / f"{fingerprint}-{lease}.json"
    _attempt(attempt, fingerprint, lease, route="KNOWN", status="unknown")
    _decision(decision, fingerprint, lease)
    monkeypatch.setattr(DISPATCH, "_live_dispatch_owner_pids", lambda _: [])

    recovered = DISPATCH.recover_orphaned_handoffs(
        queue, self_heal, state, "2026-08-21T08:00:00Z",
    )

    item = queue["items"][fingerprint]
    assert len(recovered) == 1
    assert item["state"] == "WAIT"
    assert "lease_id" not in item
    assert item["next_action"] == "WAIT_FOR_NEW_OCCURRENCE"
    assert item["lease_recovery"]["kind"] == "known-runbook"
    assert "decision_receipt" in item["lease_recovery"]["proof"]


def test_unknown_terminal_investigation_moves_to_wait(tmp_path: Path, monkeypatch) -> None:
    state = tmp_path / "state"
    self_heal = state / "self-heal"
    fingerprint, lease = "b" * 64, "repair-unknown"
    queue = _queue(fingerprint, lease)
    attempt = self_heal / "repair-attempts" / f"{fingerprint}-{lease}.json"
    investigation = self_heal / "investigations" / f"{fingerprint}-{lease}.json"
    _attempt(attempt, fingerprint, lease, route="UNKNOWN", status="COMPLETED")
    _investigation(investigation, fingerprint)
    monkeypatch.setattr(DISPATCH, "_live_dispatch_owner_pids", lambda _: [])

    recovered = DISPATCH.recover_orphaned_handoffs(
        queue, self_heal, state, "2026-08-21T08:00:00Z",
    )

    assert len(recovered) == 1
    item = queue["items"][fingerprint]
    assert item["state"] == "WAIT"
    assert item["lease_recovery"]["model_status"] == "COMPLETED"
    assert "investigation_receipt" in item["lease_recovery"]["proof"]


def test_missing_receipt_or_live_owner_stays_claimed(tmp_path: Path, monkeypatch) -> None:
    state = tmp_path / "state"
    self_heal = state / "self-heal"
    fingerprint, lease = "c" * 64, "repair-unproven"
    queue = _queue(fingerprint, lease)
    monkeypatch.setattr(DISPATCH, "_live_dispatch_owner_pids", lambda _: [])

    assert DISPATCH.recover_orphaned_handoffs(
        queue, self_heal, state, "2026-08-21T08:00:00Z",
    ) == []
    assert queue["items"][fingerprint]["state"] == "CLAIMED"

    attempt = self_heal / "repair-attempts" / f"{fingerprint}-{lease}.json"
    investigation = self_heal / "investigations" / f"{fingerprint}-{lease}.json"
    _attempt(attempt, fingerprint, lease, route="UNKNOWN", status="COMPLETED")
    _investigation(investigation, fingerprint)
    monkeypatch.setattr(DISPATCH, "_live_dispatch_owner_pids", lambda _: [12345])
    assert DISPATCH.recover_orphaned_handoffs(
        queue, self_heal, state, "2026-08-21T08:00:00Z",
    ) == []
    assert queue["items"][fingerprint]["state"] == "CLAIMED"


def test_wait_reopens_only_on_a_new_occurrence() -> None:
    work = {
        "work_id": "new", "phase": "metrics", "reason": "x",
        "source_receipt": {"path": "gates/metrics.json"},
    }
    fingerprint = QUEUE._legacy_fingerprint(work)
    queue = {
        "schema": "writer.self-heal.incident-queue", "version": 1,
        "items": {fingerprint: {
            "fingerprint": fingerprint, "state": "WAIT",
            "next_action": "WAIT_FOR_NEW_OCCURRENCE",
            "occurrences": [{"work_id": "old"}], "occurrence_count": 1,
        }},
    }
    replay = {
        "schema": "writer.observability.slo-replay",
        "slo_work": [work],
    }

    QUEUE.ingest(queue, replay, "2026-08-21T08:00:00Z")

    assert queue["items"][fingerprint]["state"] == "OPEN"


def test_duplicate_media_quarantine_hides_only_same_run_actionable_items(
    tmp_path: Path, monkeypatch,
) -> None:
    state = tmp_path / "state"
    run_id = "20260821-054500"
    gates = state / "runs" / run_id / "gates"
    gates.mkdir(parents=True)
    state_path = gates / "publication-state.json"
    state_value = {
        "run_id": run_id,
        "publication_contract": "active-four",
        "state_path": str(state_path),
        "pairs": {
            pair: {"status": "unavailable"}
            for pair in DISPATCH.ACTIVE_PUBLICATION_PAIRS
        },
    }
    state_path.write_text(json.dumps(state_value))
    quarantine = gates / "run-quarantine.json"
    quarantine.write_text(json.dumps({
        "type": "run-quarantine", "version": 1,
        "reason": "duplicate-media", "run_id": run_id,
        "state_sha256": hashlib.sha256(state_path.read_bytes()).hexdigest(),
        "headline_sha256": "a" * 64, "body_sha256": ["a" * 64],
    }))
    first, second = "e" * 64, "f" * 64
    queue = {
        "schema": "writer.self-heal.incident-queue", "version": 1,
        "items": {
            first: {"fingerprint": first, "run_id": run_id, "state": "RETRY"},
            second: {"fingerprint": second, "run_id": run_id, "state": "OPEN"},
            "g" * 64: {"fingerprint": "g" * 64, "run_id": "other", "state": "OPEN"},
        },
    }
    monkeypatch.setattr(DISPATCH, "_live_dispatch_owner_pids", lambda _: [])

    result = DISPATCH.quarantine_invalid_run_handoffs(
        queue, state, "2026-08-21T08:00:00Z",
    )

    assert {row["fingerprint"] for row in result} == {first, second}
    assert queue["items"][first]["state"] == "WAIT"
    assert queue["items"][second]["state"] == "WAIT"
    assert queue["items"]["g" * 64]["state"] == "OPEN"
    assert queue["items"][first]["queue_quarantine"]["reason"] == (
        "duplicate-media-run-isolated"
    )


def test_quarantine_proof_refuses_a_live_pair(tmp_path: Path) -> None:
    state = tmp_path / "state"
    run_id = "20260821-054500"
    gates = state / "runs" / run_id / "gates"
    gates.mkdir(parents=True)
    state_path = gates / "publication-state.json"
    state_path.write_text(json.dumps({
        "run_id": run_id, "publication_contract": "active-four",
        "state_path": str(state_path),
        "pairs": {pair: {"status": "live"} for pair in DISPATCH.ACTIVE_PUBLICATION_PAIRS},
    }))
    (gates / "run-quarantine.json").write_text(json.dumps({
        "type": "run-quarantine", "version": 1,
        "reason": "duplicate-media", "run_id": run_id,
        "state_sha256": hashlib.sha256(state_path.read_bytes()).hexdigest(),
        "headline_sha256": "a" * 64, "body_sha256": ["a" * 64],
    }))

    assert DISPATCH._quarantine_receipt_for_run(state, run_id) is None
