from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest


GIG_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = GIG_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import application_effect_fence as fence  # noqa: E402
import connector_outbox as outbox  # noqa: E402
from provider_authorization import AuthorizationDecision, AuthorizationState  # noqa: E402


HASH = "a" * 64
AUTH_HASH = "b" * 64


def _authorization(
    state: AuthorizationState = AuthorizationState.APPROVED_BROWSER,
    receipt_hash: str | None = AUTH_HASH,
) -> AuthorizationDecision:
    return AuthorizationDecision(
        state=state,
        reason="matching_receipt" if receipt_hash else "revoked",
        evidence_hash="c" * 64 if receipt_hash else None,
        receipt_hash=receipt_hash,
    )


def _intent(authorization: AuthorizationDecision | None = None):
    return fence.authorized_provider_intent(
        provider="upwork",
        account_key="account-hash",
        resource_id="job-1",
        action="submit_proposal",
        payload_hash=HASH,
        authorization=authorization or _authorization(),
    )


def _database(tmp_path: Path) -> outbox.ConnectorOutbox:
    manifest = GIG_ROOT / "config" / "connectors" / "coconala.json"
    return outbox.ConnectorOutbox(tmp_path / "outbox.sqlite3", manifest)


def test_coconala_fixture_identity_and_schema_remain_byte_for_byte(tmp_path: Path):
    lease = {"task": "apply", "token": "1" * 32, "generation": 1}
    assert fence.intent_payload(
        request_id="123",
        snapshot_sha256="2" * 64,
        proposal_text="提案です",
        price_jpy=9000,
        deliver_date="2026-08-30",
        lease_fence=lease,
    ) == {
        "version": 2,
        "state": "prepared",
        "effect_phase": "pre_effect",
        "request_id": "123",
        "snapshot_sha256": "2" * 64,
        "proposal_sha256": fence.proposal_sha256("提案です"),
        "price_jpy": 9000,
        "deliver_date": "2026-08-30",
        "lease_fence": lease,
        "cas": fence.build_cas(
            "123", "2" * 64, fence.proposal_sha256("提案です"), 9000, "2026-08-30",
        ),
    }
    assert outbox.coconala_message_event_key("123", "buyer-1") == (
        "coconala:message:v1:123:buyer-1"
    )
    database = _database(tmp_path)
    with sqlite3.connect(database.database) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(connector_intents)")}
    assert "authorization_hash" not in columns


@pytest.mark.parametrize(
    "authorization",
    [
        AuthorizationDecision(AuthorizationState.UNKNOWN, "missing"),
        AuthorizationDecision(AuthorizationState.DENIED, "revoked"),
        AuthorizationDecision(AuthorizationState.APPROVED_BROWSER, "missing_hash"),
    ],
)
def test_missing_or_revoked_authorization_cannot_create_intent(authorization):
    with pytest.raises(fence.IntentFenceError, match="authorization_not_approved"):
        _intent(authorization)


def test_same_receipt_and_payload_replay_creates_one_durable_intent(tmp_path: Path):
    database = _database(tmp_path)
    authorization = _authorization()
    intent = _intent(authorization)
    first = database.prepare_provider_effect(intent, authorization=authorization, now=100)
    replay = database.prepare_provider_effect(intent, authorization=authorization, now=101)
    assert first["created"] is True and first["reconcile_only"] is False
    assert replay["created"] is False and replay["reconcile_only"] is True
    with sqlite3.connect(database.database) as connection:
        count = connection.execute("SELECT COUNT(*) FROM provider_effect_intents").fetchone()[0]
    assert count == 1


def test_changed_authorization_cannot_reuse_logical_effect(tmp_path: Path):
    database = _database(tmp_path)
    first_authorization = _authorization()
    first_intent = _intent(first_authorization)
    database.prepare_provider_effect(first_intent, authorization=first_authorization, now=100)

    changed_authorization = _authorization(receipt_hash="d" * 64)
    changed_intent = _intent(changed_authorization)
    assert changed_intent.effect_key == first_intent.effect_key
    with pytest.raises(outbox.ImmutableIntent, match="authorization hash cannot change"):
        database.prepare_provider_effect(
            changed_intent, authorization=changed_authorization, now=101,
        )


def test_revocation_between_prepare_and_effect_prevents_start(tmp_path: Path):
    database = _database(tmp_path)
    authorization = _authorization()
    intent = _intent(authorization)
    database.prepare_provider_effect(intent, authorization=authorization, now=100)
    revoked = AuthorizationDecision(AuthorizationState.DENIED, "revoked")
    with pytest.raises(outbox.ConnectorDisabled, match="authorization_not_approved"):
        database.mark_provider_effect_started(intent, authorization=revoked, now=101)


def test_lost_ack_stays_reconcile_only_and_never_prepares_second_effect(tmp_path: Path):
    database = _database(tmp_path)
    authorization = _authorization()
    intent = _intent(authorization)
    database.prepare_provider_effect(intent, authorization=authorization, now=100)
    started = database.mark_provider_effect_started(intent, authorization=authorization, now=101)
    repeated_start = database.mark_provider_effect_started(
        intent, authorization=authorization, now=102,
    )
    replay = database.prepare_provider_effect(intent, authorization=authorization, now=103)
    assert started["state"] == "reconcile_pending"
    assert started["started"] is True and started["reconcile_only"] is False
    assert repeated_start["started"] is False
    assert repeated_start["reconcile_only"] is True
    assert replay["state"] == "reconcile_pending"
    assert replay["created"] is False and replay["reconcile_only"] is True


def test_official_no_effect_and_unchanged_balance_reopen_exact_intent(tmp_path: Path):
    database = _database(tmp_path)
    authorization = _authorization()
    intent = _intent(authorization)
    database.prepare_provider_effect(
        intent, authorization=authorization, now=100, connects_pre=10,
        connects_pre_hash="a" * 64, payload_body='{"sealed":true}',
    )
    database.mark_provider_effect_started(intent, authorization=authorization, now=101)

    reopened = database.reopen_provider_effect_after_no_effect(
        intent, authorization=authorization, connects_current=10,
        connects_evidence_sha256="b" * 64, no_effect_readback_hash="c" * 64, now=102,
    )
    restarted = database.mark_provider_effect_started(
        intent, authorization=authorization, now=103,
    )

    assert (reopened["state"], reopened["reconciliation_state"]) == ("prepared", "not_started")
    assert reopened["connects_pre_hash"] == "b" * 64
    assert restarted["started"] is True


def test_official_no_effect_reopens_after_verified_intervening_spend(tmp_path: Path):
    database = _database(tmp_path)
    authorization = _authorization()
    stale = _intent(authorization)
    database.prepare_provider_effect(
        stale, authorization=authorization, now=100, connects_pre=67,
        connects_pre_hash="a" * 64, payload_body='{"sealed":true}',
    )
    database.mark_provider_effect_started(stale, authorization=authorization, now=101)
    later = fence.authorized_provider_intent(
        provider="upwork", account_key="account-hash", resource_id="job-2",
        action="submit_proposal", payload_hash="d" * 64, authorization=authorization,
    )
    database.prepare_provider_effect(
        later, authorization=authorization, now=102, connects_pre=67,
        connects_pre_hash="e" * 64, payload_body='{"sealed":true}',
    )
    database.mark_provider_effect_started(later, authorization=authorization, now=103)
    database.verify_provider_effect(
        later, proposal_id="proposal-2", connects_post=46,
        readback_hash="f" * 64, now=104,
    )

    reopened = database.reopen_provider_effect_after_no_effect(
        stale, authorization=authorization, connects_current=46,
        connects_evidence_sha256="1" * 64, no_effect_readback_hash="2" * 64, now=105,
    )

    assert (reopened["state"], reopened["connects_pre"]) == ("prepared", 46)
