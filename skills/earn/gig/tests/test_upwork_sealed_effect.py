from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest


GIG_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = GIG_ROOT / "scripts"
PROVIDERS = SCRIPTS / "providers"
for directory in (SCRIPTS, PROVIDERS):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from application_effect_fence import authorized_provider_intent  # noqa: E402
from connector_outbox import ConnectorOutbox  # noqa: E402
from provider_authorization import AuthorizationDecision, AuthorizationState  # noqa: E402
from upwork_sealed_effect import SealedUpworkProposalEffect  # noqa: E402


AUTH = AuthorizationDecision(
    AuthorizationState.APPROVED_BROWSER, "matching_receipt",
    evidence_hash="a" * 64, receipt_hash="b" * 64,
)


class Selection:
    authorization = AUTH


class Transport:
    def for_action(self, action):
        return Selection() if action == "propose" else None

    def effect_intent(self, selection, *, resource_id, payload_hash):
        return authorized_provider_intent(
            provider="upwork", account_key="owner", resource_id=resource_id,
            action="propose", payload_hash=payload_hash,
            authorization=selection.authorization,
        )


def _payload():
    return {
        "provider": "upwork", "job_id": "~012345678901234",
        "payload_sha256": "c" * 64,
        "terms": {"required_connects": 7}, "cover_letter": "private",
    }


def _preflight(**changes):
    value = {
        "ready": True, "job_id": "~012345678901234", "required_connects": 7,
        "available_connects": 7, "evidence_sha256": "d" * 64,
    }
    value.update(changes)
    return value


def _effect(tmp_path):
    store = ConnectorOutbox(
        tmp_path / "outbox.sqlite3", GIG_ROOT / "config/connectors/coconala.json",
    )
    return SealedUpworkProposalEffect(store, Transport(), now_epoch=lambda: 100), store


def _row(store):
    with sqlite3.connect(store.database) as connection:
        connection.row_factory = sqlite3.Row
        return dict(connection.execute("SELECT * FROM provider_effect_intents").fetchone())


def test_exact_preflight_persists_then_starts_one_effect(tmp_path):
    effect, store = _effect(tmp_path)

    intent, started = effect.start(_payload(), _preflight())

    assert started is True
    assert intent.resource_id == "~012345678901234"
    assert _row(store)["state"] == "reconcile_pending"
    assert _row(store)["connects_pre"] == 7
    assert "private" in _row(store)["payload_body"]
    assert store.database.stat().st_mode & 0o777 == 0o600


def test_replay_never_starts_a_second_click(tmp_path):
    effect, _ = _effect(tmp_path)
    first, started = effect.start(_payload(), _preflight())

    replay, replay_started = effect.start(_payload(), _preflight())

    assert started is True and replay_started is False
    assert replay.effect_key == first.effect_key


def test_insufficient_live_form_balance_creates_no_effect(tmp_path):
    effect, store = _effect(tmp_path)

    with pytest.raises(ValueError, match="upwork_preflight_effect_mismatch"):
        effect.start(_payload(), _preflight(available_connects=6))

    with sqlite3.connect(store.database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM provider_effect_intents").fetchone()[0] == 0


def test_exact_proposal_and_post_connects_verify_effect(tmp_path):
    effect, store = _effect(tmp_path)
    intent, _ = effect.start(_payload(), _preflight())

    effect.verify(intent, {
        "state": "submitted", "job_id": intent.resource_id,
        "proposal_id": "proposal-1", "evidence_sha256": "e" * 64,
    }, connects_post=0, connects_evidence_sha256="f" * 64)

    assert _row(store)["reconciliation_state"] == "verified"
    assert _row(store)["proposal_id"] == "proposal-1"
    assert _row(store)["connects_post"] == 0


def test_wrong_post_connects_delta_never_verifies_effect(tmp_path):
    effect, store = _effect(tmp_path)
    intent, _ = effect.start(_payload(), _preflight())

    with pytest.raises(ValueError, match="upwork_connects_effect_mismatch"):
        effect.verify(intent, {
            "state": "submitted", "job_id": intent.resource_id,
            "proposal_id": "proposal-1", "evidence_sha256": "e" * 64,
        }, connects_post=1, connects_evidence_sha256="f" * 64)

    assert _row(store)["reconciliation_state"] == "reconcile_unknown"
