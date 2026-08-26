#!/usr/bin/env python3
"""Provider-neutral records and effect/readback contract for Gig markets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


class ContractViolation(ValueError):
    """A provider adapter or canonical record violated the commerce contract."""


def _text(label: str, value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ContractViolation(f"invalid_{label}")


def _hash(label: str, value: Any) -> None:
    _text(label, value)
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ContractViolation(f"invalid_{label}")


def _time(label: str, value: Any) -> None:
    _text(label, value)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractViolation(f"invalid_{label}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ContractViolation(f"invalid_{label}")


def _currency(value: Any) -> None:
    if not isinstance(value, str) or len(value) != 3 or not value.isalpha() or not value.isupper():
        raise ContractViolation("invalid_currency")


def _minor(label: str, value: Any) -> None:
    if type(value) is not int or value < 0:
        raise ContractViolation(f"invalid_{label}")


@dataclass(frozen=True)
class Opportunity:
    provider: str
    opportunity_id: str
    source_url: str
    title: str
    currency: str
    source_hash: str
    observed_at: str

    def __post_init__(self) -> None:
        for label in ("provider", "opportunity_id", "source_url", "title"):
            _text(label, getattr(self, label))
        _currency(self.currency)
        _hash("source_hash", self.source_hash)
        _time("observed_at", self.observed_at)


@dataclass(frozen=True)
class OpportunityDetail:
    opportunity: Opportunity
    scope: str
    source_hash: str

    def __post_init__(self) -> None:
        if not isinstance(self.opportunity, Opportunity):
            raise ContractViolation("invalid_opportunity")
        _text("scope", self.scope)
        _hash("source_hash", self.source_hash)


@dataclass(frozen=True)
class EffectIntent:
    provider: str
    account_key: str
    resource_id: str
    action: str
    payload_hash: str
    authorization_hash: str
    effect_key: str

    def __post_init__(self) -> None:
        for label in ("provider", "account_key", "resource_id", "action", "effect_key"):
            _text(label, getattr(self, label))
        _hash("payload_hash", self.payload_hash)
        _hash("authorization_hash", self.authorization_hash)


@dataclass(frozen=True)
class ProviderReceipt:
    provider: str
    action: str
    effect_key: str
    provider_receipt_id: str
    authoritative_state: str
    observed_at: str
    evidence_hash: str

    def __post_init__(self) -> None:
        for label in (
            "provider", "action", "effect_key", "provider_receipt_id", "authoritative_state",
        ):
            _text(label, getattr(self, label))
        _time("observed_at", self.observed_at)
        _hash("evidence_hash", self.evidence_hash)


@dataclass(frozen=True)
class ProviderState:
    provider: str
    resource_id: str
    action: str
    state: str
    observed_at: str
    evidence_hash: str

    def __post_init__(self) -> None:
        for label in ("provider", "resource_id", "action", "state"):
            _text(label, getattr(self, label))
        _time("observed_at", self.observed_at)
        _hash("evidence_hash", self.evidence_hash)


@dataclass(frozen=True)
class TransportAck:
    provider: str
    action: str
    effect_key: str
    accepted: bool
    ack_id: str | None

    def __post_init__(self) -> None:
        for label in ("provider", "action", "effect_key"):
            _text(label, getattr(self, label))
        if type(self.accepted) is not bool:
            raise ContractViolation("invalid_accepted")
        if self.ack_id is not None:
            _text("ack_id", self.ack_id)


@dataclass(frozen=True)
class ProjectState:
    provider: str
    project_id: str
    opportunity_id: str
    state: str
    observed_at: str
    evidence_hash: str

    def __post_init__(self) -> None:
        for label in ("provider", "project_id", "opportunity_id", "state"):
            _text(label, getattr(self, label))
        _time("observed_at", self.observed_at)
        _hash("evidence_hash", self.evidence_hash)


@dataclass(frozen=True)
class PaymentState:
    provider: str
    payment_id: str
    project_id: str
    currency: str
    gross_minor: int
    fee_minor: int
    state: str
    observed_at: str
    evidence_hash: str

    def __post_init__(self) -> None:
        for label in ("provider", "payment_id", "project_id", "state"):
            _text(label, getattr(self, label))
        _currency(self.currency)
        _minor("gross_minor", self.gross_minor)
        _minor("fee_minor", self.fee_minor)
        _time("observed_at", self.observed_at)
        _hash("evidence_hash", self.evidence_hash)


class ProviderAdapter(Protocol):
    def discover(self) -> list[Opportunity]: ...
    def inspect(self, opportunity_id: str) -> OpportunityDetail: ...
    def plan_effect(self, action: str, payload: dict[str, Any]) -> EffectIntent: ...
    def reconcile(self, intent: EffectIntent) -> ProviderState: ...
    def execute(self, intent: EffectIntent) -> TransportAck: ...
    def readback(self, intent: EffectIntent) -> ProviderReceipt: ...
    def list_projects(self) -> list[ProjectState]: ...
    def list_payments(self) -> list[PaymentState]: ...


_OPERATIONS = (
    "discover", "inspect", "plan_effect", "reconcile", "execute", "readback",
    "list_projects", "list_payments",
)


def validate_adapter(adapter: Any) -> Any:
    for operation in _OPERATIONS:
        if not callable(getattr(adapter, operation, None)):
            raise ContractViolation(f"missing_adapter_operation:{operation}")
    return adapter


def validate_effect_result(
    intent: EffectIntent,
    ack: TransportAck,
    receipt: ProviderReceipt | None,
) -> ProviderReceipt:
    if receipt is None:
        raise ContractViolation("authoritative_readback_required")
    expected = (intent.provider, intent.action, intent.effect_key)
    actual = (receipt.provider, receipt.action, receipt.effect_key)
    if actual != expected:
        raise ContractViolation("readback_identity_mismatch")
    return receipt
