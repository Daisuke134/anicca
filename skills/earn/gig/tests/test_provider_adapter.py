from __future__ import annotations

import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from provider_adapter import (  # noqa: E402
    ContractViolation,
    EffectIntent,
    Opportunity,
    OpportunityDetail,
    PaymentState,
    ProjectState,
    ProviderReceipt,
    ProviderState,
    TransportAck,
    validate_adapter,
    validate_effect_result,
)


HASH = "a" * 64
OBSERVED = "2026-08-22T08:30:00Z"


def _opportunity(**overrides: object) -> Opportunity:
    value: dict[str, object] = {
        "provider": "upwork",
        "opportunity_id": "job-1",
        "source_url": "https://example.invalid/jobs/job-1",
        "title": "Build a bounded adapter",
        "currency": "USD",
        "source_hash": HASH,
        "observed_at": OBSERVED,
    }
    value.update(overrides)
    return Opportunity(**value)


def _intent(**overrides: object) -> EffectIntent:
    value = {
        "provider": "upwork",
        "account_key": "account-hash",
        "resource_id": "job-1",
        "action": "submit_proposal",
        "payload_hash": HASH,
        "authorization_hash": "b" * 64,
        "effect_key": "upwork:job-1:submit_proposal:" + HASH,
    }
    value.update(overrides)
    return EffectIntent(**value)


def _receipt(**overrides: object) -> ProviderReceipt:
    value = {
        "provider": "upwork",
        "action": "submit_proposal",
        "effect_key": "upwork:job-1:submit_proposal:" + HASH,
        "provider_receipt_id": "proposal-9",
        "authoritative_state": "submitted",
        "observed_at": OBSERVED,
        "evidence_hash": "c" * 64,
    }
    value.update(overrides)
    return ProviderReceipt(**value)


def test_domain_records_are_frozen_and_require_canonical_evidence():
    opportunity = _opportunity()
    with pytest.raises(FrozenInstanceError):
        opportunity.title = "changed"

    detail = OpportunityDetail(opportunity=opportunity, scope="One adapter", source_hash=HASH)
    project = ProjectState(
        provider="upwork", project_id="contract-1", opportunity_id="job-1",
        state="active", observed_at=OBSERVED, evidence_hash=HASH,
    )
    payment = PaymentState(
        provider="upwork", payment_id="txn-1", project_id="contract-1", currency="USD",
        gross_minor=10_000, fee_minor=1_000, state="released", observed_at=OBSERVED,
        evidence_hash=HASH,
    )
    assert detail.opportunity.opportunity_id == "job-1"
    assert project.project_id == "contract-1"
    assert payment.gross_minor - payment.fee_minor == 9_000


@pytest.mark.parametrize(
    "override",
    [
        {"provider": ""},
        {"opportunity_id": ""},
        {"currency": "usd"},
        {"source_hash": "not-a-sha256"},
        {"observed_at": "not-a-timestamp"},
    ],
)
def test_opportunity_rejects_missing_or_noncanonical_fields(override: dict[str, str]):
    with pytest.raises(ContractViolation):
        _opportunity(**override)


class FakeAdapter:
    def discover(self):
        return []

    def inspect(self, opportunity_id):
        return OpportunityDetail(_opportunity(opportunity_id=opportunity_id), "scope", HASH)

    def plan_effect(self, action, payload):
        return _intent(action=action)

    def reconcile(self, intent):
        return ProviderState(
            intent.provider, intent.resource_id, intent.action, "absent", OBSERVED, HASH,
        )

    def execute(self, intent):
        return TransportAck(intent.provider, intent.action, intent.effect_key, True, "ack-1")

    def readback(self, intent):
        return _receipt(action=intent.action, effect_key=intent.effect_key)

    def list_projects(self):
        return []

    def list_payments(self):
        return []


def test_runtime_adapter_validator_requires_all_eight_operations():
    adapter = FakeAdapter()
    assert validate_adapter(adapter) is adapter
    adapter.readback = None
    with pytest.raises(ContractViolation, match="missing_adapter_operation:readback"):
        validate_adapter(adapter)


def test_transport_ack_cannot_become_success_without_authoritative_readback():
    intent = _intent()
    ack = TransportAck(intent.provider, intent.action, intent.effect_key, True, "ack-1")
    with pytest.raises(ContractViolation, match="authoritative_readback_required"):
        validate_effect_result(intent, ack, None)


@pytest.mark.parametrize(
    "receipt_override",
    [
        {"provider": "fiverr"},
        {"action": "send_message"},
        {"effect_key": "different-effect"},
    ],
)
def test_readback_must_match_provider_action_and_effect_key(receipt_override: dict[str, str]):
    intent = _intent()
    ack = TransportAck(intent.provider, intent.action, intent.effect_key, True, "ack-1")
    with pytest.raises(ContractViolation, match="readback_identity_mismatch"):
        validate_effect_result(intent, ack, _receipt(**receipt_override))


def test_matching_authoritative_readback_is_the_success_receipt():
    intent = _intent()
    ack = TransportAck(intent.provider, intent.action, intent.effect_key, True, "ack-1")
    receipt = _receipt()
    assert validate_effect_result(intent, ack, receipt) is receipt
