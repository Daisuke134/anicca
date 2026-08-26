from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest


GIG = Path(__file__).resolve().parents[1]
SCRIPTS, PROVIDERS = GIG / "scripts", GIG / "scripts" / "providers"
for directory in (SCRIPTS, PROVIDERS):
    sys.path.insert(0, str(directory))

from application_effect_fence import authorized_provider_intent  # noqa: E402
from connector_outbox import ConnectorOutbox, ImmutableIntent  # noqa: E402
from provider_authorization import AuthorizationDecision, AuthorizationState  # noqa: E402
from upwork_delivery import UpworkMilestoneDelivery  # noqa: E402


NOW = datetime(2026, 8, 23, tzinfo=timezone.utc)
ACCOUNT = "upwork-owner:v1:" + "1" * 64


class Selection:
    mode = "cloak_browser"
    authorization = AuthorizationDecision(
        AuthorizationState.APPROVED_BROWSER, "matching_receipt",
        evidence_hash="a" * 64, receipt_hash="b" * 64,
    )


class Transport:
    def for_action(self, action):
        return Selection() if action == "deliver_milestone" else None

    def effect_intent(self, selection, *, resource_id, payload_hash):
        return authorized_provider_intent(
            provider="upwork", account_key=ACCOUNT, resource_id=resource_id,
            action="deliver_milestone", payload_hash=payload_hash,
            authorization=selection.authorization,
        )


class Provider:
    def __init__(self, mode="success"):
        self.mode, self.submits, self.record = mode, 0, None

    def read_contract(self, selection, contract_id, milestone_id):
        return {
            "contract_id": contract_id, "milestone_id": milestone_id,
            "contract_sha256": "f" * 64,
            "milestone_state": "active", "funded": True,
            "workroom_url": f"https://www.upwork.com/ab/f/contracts/{contract_id}",
            "observed_at": NOW.isoformat(), "evidence_sha256": "c" * 64,
        }

    def submit(self, selection, intent, payload):
        self.submits += 1
        self.record = {
            "state": "submitted", "submission_id": "submission-9",
            "contract_id": payload["contract_id"], "milestone_id": payload["milestone_id"],
            "artifact_sha256": payload["artifact_sha256"],
            "evidence_sha256": "d" * 64,
        }
        if self.mode == "lost_ack":
            raise TimeoutError("ack lost")
        return self.record

    def read_submission(self, selection, intent):
        return self.record


def _inputs(tmp_path: Path):
    root = tmp_path / "project"; root.mkdir()
    artifact = root / "artifact.txt"; artifact.write_text("finished work", encoding="utf-8")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    execution = {
        "state": "completed", "execution_id": "e" * 64, "contract_sha256": "f" * 64,
        "artifacts": [{"path": "artifact.txt", "sha256": digest, "bytes": 13}],
    }
    verification = {
        "status": "PASS", "delivery_intent_permitted": True,
        "artifact_sha256": [digest], "contract_clause": "Deliver finished work",
        "evidence": ["artifact_hash_verified", "independent_context_verified"],
    }
    return root, execution, verification


def _lane(tmp_path: Path, provider: Provider):
    store = ConnectorOutbox(
        tmp_path / "outbox.sqlite3", GIG / "config/connectors/coconala.json",
    )
    lane = UpworkMilestoneDelivery(
        store, Transport(), provider.read_contract, provider.submit,
        provider.read_submission, now=lambda: NOW,
    )
    return lane, store


@pytest.mark.parametrize("mode", ["success", "lost_ack"])
def test_repeated_tick_and_lost_ack_submit_one_frozen_milestone(tmp_path, mode):
    provider = Provider(mode); lane, store = _lane(tmp_path, provider)
    root, execution, verification = _inputs(tmp_path)
    intent = lane.plan(
        workspace=root, contract_id="contract-1", milestone_id="milestone-1",
        execution_receipt=execution, verification=verification,
        message="Completed exactly the funded milestone.",
    )

    first = lane.execute(intent)
    replay = lane.execute(intent)

    assert first["state"] == replay["state"] == "submitted"
    assert first["submission_id"] == "submission-9"
    assert provider.submits == 1
    with sqlite3.connect(store.database) as connection:
        row = connection.execute(
            "SELECT state,reconciliation_state,proposal_id FROM provider_effect_intents"
        ).fetchone()
    assert row == ("reconcile_pending", "verified", "submission-9")


def test_changed_artifact_cannot_replace_a_milestone_intent(tmp_path):
    provider = Provider(); lane, _ = _lane(tmp_path, provider)
    root, execution, verification = _inputs(tmp_path)
    lane.plan(workspace=root, contract_id="contract-1", milestone_id="milestone-1",
              execution_receipt=execution, verification=verification, message="Done")
    changed = root / "changed.txt"; changed.write_text("different", encoding="utf-8")
    digest = hashlib.sha256(changed.read_bytes()).hexdigest()
    execution = {**execution, "artifacts": [{"path": "changed.txt", "sha256": digest, "bytes": 9}]}
    verification = {**verification, "artifact_sha256": [digest]}

    with pytest.raises(ImmutableIntent):
        lane.plan(workspace=root, contract_id="contract-1", milestone_id="milestone-1",
                  execution_receipt=execution, verification=verification, message="Done")
    assert provider.submits == 0


@pytest.mark.parametrize("fault", ["not_pass", "forged_pass", "not_funded"])
def test_invalid_verification_or_contract_never_persists_intent(tmp_path, fault):
    provider = Provider(); lane, store = _lane(tmp_path, provider)
    root, execution, verification = _inputs(tmp_path)
    if fault == "not_pass":
        verification = {**verification, "status": "REVISE", "delivery_intent_permitted": False}
    elif fault == "forged_pass":
        verification = {**verification, "evidence": ["artifact_hash_verified"]}
    else:
        original = provider.read_contract
        lane.read_contract = lambda *args: {**original(*args), "funded": False}

    with pytest.raises(ValueError):
        lane.plan(workspace=root, contract_id="contract-1", milestone_id="milestone-1",
                  execution_receipt=execution, verification=verification, message="Done")
    with sqlite3.connect(store.database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM provider_effect_intents").fetchone()[0] == 0
