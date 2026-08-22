"""Crash matrix for exactly-once Upwork proposal effects."""

from __future__ import annotations

import json
import sqlite3
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest


GIG_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = GIG_ROOT / "scripts"
PROVIDERS = SCRIPTS / "providers"
for directory in (SCRIPTS, PROVIDERS):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from application_effect_fence import authorized_provider_intent  # noqa: E402
from connector_outbox import ConnectorOutbox, ImmutableIntent  # noqa: E402
from provider_adapter import TransportAck  # noqa: E402
from provider_authorization import AuthorizationDecision, AuthorizationState  # noqa: E402
from upwork_adapter import UpworkAdapter  # noqa: E402
from upwork_proposal import (  # noqa: E402
    Attachment, Claim, Milestone, ProposalPayload, payload_sha256,
)


ACCOUNT = "upwork-owner:v1:" + "1" * 64
AUTH_HASH = "b" * 64
NOW = datetime(2026, 8, 23, tzinfo=timezone.utc)


def _payload(**overrides: object) -> ProposalPayload:
    value = {
        "version": 1,
        "provider": "upwork",
        "opportunity_id": "~0123456789012345678",
        "opportunity_source_hash": "a" * 64,
        "qualification_sha256": "2" * 64,
        "currency": "USD",
        "pricing_kind": "fixed",
        "bid_minor": 90_000,
        "connects_cost": 12,
        "estimated_duration_days": 2,
        "cover_letter": "Exact bounded adapter proposal",
        "scope_references": ("bounded adapter",),
        "milestones": (Milestone("Delivery", "Adapter and tests", "2026-08-25T00:00:00+00:00", 90_000),),
        "claims": (Claim("Tested delivery", "asset-1", "3" * 64),),
        "attachments": (Attachment("sample.pdf", "asset-2", "4" * 64),),
        "workflow_skill": "builder",
        "verifier_sha256": "5" * 64,
        "payload_hash": "",
    }
    value.update(overrides)
    payload = ProposalPayload(**value)
    if not payload.payload_hash:
        payload = replace(payload, payload_hash=payload_sha256(payload))
    return payload


def _authorization() -> AuthorizationDecision:
    return AuthorizationDecision(
        AuthorizationState.APPROVED_BROWSER, "matching_receipt",
        evidence_hash="c" * 64, receipt_hash=AUTH_HASH,
    )


class Selection:
    mode = "cloak_browser"
    authorization = _authorization()


class Transport:
    def for_action(self, action: str):
        return Selection() if action == "propose" else None

    def effect_intent(self, selection, *, resource_id: str, payload_hash: str):
        return authorized_provider_intent(
            provider="upwork", account_key=ACCOUNT, resource_id=resource_id,
            action="propose", payload_hash=payload_hash,
            authorization=selection.authorization,
        )


class Provider:
    def __init__(self, mode: str = "success"):
        self.mode = mode
        self.connects = 40
        self.submits = 0
        self.record: dict[str, object] | None = None

    def read_connects(self, selection):
        return {
            "balance": self.connects, "observed_at": NOW.isoformat(),
            "evidence_hash": "7" * 64,
        }

    def submit(self, selection, intent, payload):
        self.submits += 1
        if self.mode in {"success", "lost_ack"}:
            self.connects -= payload["connects_cost"]
            self.record = {
                "proposal_id": "proposal-9",
                "job_id": intent.resource_id,
                "payload_hash": intent.payload_hash,
                "state": "submitted",
                "connects_balance": self.connects,
                "observed_at": NOW.isoformat(),
                "evidence_hash": "8" * 64,
            }
        if self.mode in {"lost_ack", "timeout"}:
            raise TimeoutError("provider timeout")
        return TransportAck("upwork", "propose", intent.effect_key, True, "ack-9")

    def read_proposal(self, selection, intent):
        return self.record


def _adapter(tmp_path: Path, provider: Provider):
    store = ConnectorOutbox(tmp_path / "outbox.sqlite3", GIG_ROOT / "config" / "connectors" / "coconala.json")
    adapter = UpworkAdapter(
        Transport(), lambda *_: {}, lambda *_: {}, query="python",
        effect_store=store, read_connects=provider.read_connects,
        submit_proposal=provider.submit, read_proposal=provider.read_proposal,
        now_epoch=lambda: 100,
    )
    return adapter, store


def _row(store: ConnectorOutbox) -> dict[str, object]:
    with sqlite3.connect(store.database) as connection:
        connection.row_factory = sqlite3.Row
        return dict(connection.execute("SELECT * FROM provider_effect_intents").fetchone())


def test_plan_persists_exact_identity_connects_and_payload_before_effect(tmp_path):
    provider = Provider()
    adapter, store = _adapter(tmp_path, provider)

    intent = adapter.plan_effect("propose", _payload())
    row = _row(store)

    assert row["authorization_hash"] == AUTH_HASH
    assert row["resource_id"] == _payload().opportunity_id
    assert row["payload_hash"] == _payload().payload_hash
    assert row["connects_pre"] == 40
    assert row["connects_pre_hash"] == "7" * 64
    assert json.loads(row["payload_body"])["payload_hash"] == _payload().payload_hash
    assert row["state"] == "prepared"
    assert provider.submits == 0
    assert intent.action == "propose"


def test_zero_connects_never_prepares_or_submits_a_proposal(tmp_path):
    provider = Provider()
    provider.connects = 0
    adapter, store = _adapter(tmp_path, provider)

    with pytest.raises(ValueError, match="insufficient_free_connects"):
        adapter.plan_effect("propose", _payload())

    assert provider.submits == 0
    with sqlite3.connect(store.database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM provider_effect_intents").fetchone()[0] == 0


def test_free_balance_must_cover_the_jobs_exact_connects_cost(tmp_path):
    provider = Provider()
    provider.connects = 11
    adapter, _ = _adapter(tmp_path, provider)

    with pytest.raises(ValueError, match="insufficient_free_connects"):
        adapter.plan_effect("propose", _payload())

    assert provider.submits == 0


def test_balance_drop_after_planning_is_rechecked_before_submit(tmp_path):
    provider = Provider()
    adapter, _ = _adapter(tmp_path, provider)
    intent = adapter.plan_effect("propose", _payload())
    provider.connects = 0

    with pytest.raises(ValueError, match="insufficient_free_connects"):
        adapter.execute(intent)

    assert provider.submits == 0


def test_crash_before_effect_can_resume_once_from_durable_payload(tmp_path):
    provider = Provider()
    first, _ = _adapter(tmp_path, provider)
    intent = first.plan_effect("propose", _payload())

    resumed, _ = _adapter(tmp_path, provider)
    ack = resumed.execute(intent)

    assert ack.accepted is True
    assert provider.submits == 1
    assert provider.connects == 28


def test_lost_ack_reconciles_success_without_second_submit_or_connects(tmp_path):
    provider = Provider("lost_ack")
    adapter, store = _adapter(tmp_path, provider)
    intent = adapter.plan_effect("propose", _payload())

    first = adapter.execute(intent)
    replay = adapter.execute(intent)
    receipt = adapter.readback(intent)

    assert first.accepted is False
    assert replay.accepted is True
    assert provider.submits == 1 and provider.connects == 28
    assert receipt.provider_receipt_id == "proposal-9"
    assert receipt.authoritative_state == "submitted"
    assert _row(store)["reconciliation_state"] == "verified"
    assert _row(store)["connects_post"] == 28


def test_timeout_without_readback_stays_unknown_and_never_retries(tmp_path):
    provider = Provider("timeout")
    adapter, store = _adapter(tmp_path, provider)
    intent = adapter.plan_effect("propose", _payload())

    assert adapter.execute(intent).accepted is False
    assert adapter.reconcile(intent).state == "reconcile_unknown"
    assert adapter.execute(intent).accepted is False
    assert provider.submits == 1 and provider.connects == 40
    assert _row(store)["reconciliation_state"] == "reconcile_unknown"


def test_success_readback_requires_proposal_id_and_connects_post_state(tmp_path):
    provider = Provider()
    adapter, _ = _adapter(tmp_path, provider)
    intent = adapter.plan_effect("propose", _payload())
    adapter.execute(intent)
    provider.record.pop("proposal_id")

    with pytest.raises(ValueError, match="invalid_proposal_readback"):
        adapter.readback(intent)


def test_repeated_tick_and_changed_payload_create_no_second_proposal(tmp_path):
    provider = Provider()
    adapter, _ = _adapter(tmp_path, provider)
    intent = adapter.plan_effect("propose", _payload())
    adapter.execute(intent)
    adapter.readback(intent)

    replay = adapter.plan_effect("propose", _payload())
    assert replay.effect_key == intent.effect_key
    assert adapter.execute(replay).accepted is True
    with pytest.raises(ImmutableIntent, match="resource already has proposal intent"):
        adapter.plan_effect("propose", _payload(cover_letter="Changed exact bounded adapter proposal"))
    assert provider.submits == 1 and provider.connects == 28


def test_authorization_revocation_between_plan_and_execute_blocks_effect(tmp_path):
    provider = Provider()
    adapter, _ = _adapter(tmp_path, provider)
    intent = adapter.plan_effect("propose", _payload())
    adapter.transport.for_action = lambda action: None

    with pytest.raises(ValueError, match="authorization_not_approved"):
        adapter.execute(intent)
    assert provider.submits == 0 and provider.connects == 40


def test_two_executors_racing_on_prepared_intent_submit_exactly_once(tmp_path):
    provider = Provider()
    adapter, store = _adapter(tmp_path, provider)
    intent = adapter.plan_effect("propose", _payload())
    barrier = threading.Barrier(2)
    original = store.mark_provider_effect_started

    def synchronized_start(*args, **kwargs):
        barrier.wait(timeout=5)
        return original(*args, **kwargs)

    store.mark_provider_effect_started = synchronized_start
    with ThreadPoolExecutor(max_workers=2) as pool:
        acknowledgements = list(pool.map(lambda _: adapter.execute(intent), range(2)))

    assert sum(ack.accepted for ack in acknowledgements) == 1
    assert provider.submits == 1
    assert provider.connects == 28
    assert _row(store)["state"] == "reconcile_pending"


@pytest.mark.parametrize(("field", "tampered"), (
    ("cover_letter", "Tampered proposal body"),
    ("bid_minor", 1),
))
def test_tampered_durable_payload_never_submits(tmp_path, field, tampered):
    provider = Provider()
    adapter, store = _adapter(tmp_path, provider)
    intent = adapter.plan_effect("propose", _payload())
    row = _row(store)
    body = json.loads(row["payload_body"])
    body[field] = tampered
    with sqlite3.connect(store.database) as connection:
        connection.execute(
            "UPDATE provider_effect_intents SET payload_body=? WHERE effect_key=?",
            (json.dumps(body, sort_keys=True, separators=(",", ":")), intent.effect_key),
        )

    with pytest.raises(ValueError, match="invalid_durable_proposal"):
        adapter.execute(intent)
    assert provider.submits == 0
    assert provider.connects == 40
