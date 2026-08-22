#!/usr/bin/env python3
"""Seal an Upwork proposal to job, qualification, terms, and factual claims."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Mapping

from opportunity_qualifier import Qualification


_HASH = re.compile(r"^[0-9a-f]{64}$")


class ProposalContractError(ValueError):
    """The proposal is generic, unsupported, or not bound to qualification."""


@dataclass(frozen=True)
class Milestone:
    title: str
    deliverable: str
    due_at: str
    amount_minor: int


@dataclass(frozen=True)
class Claim:
    text: str
    evidence_id: str
    evidence_sha256: str


@dataclass(frozen=True)
class Attachment:
    name: str
    evidence_id: str
    content_sha256: str


@dataclass(frozen=True)
class ProposalPayload:
    version: int
    provider: str
    opportunity_id: str
    opportunity_source_hash: str
    qualification_sha256: str
    currency: str
    pricing_kind: str
    bid_minor: int
    connects_cost: int
    estimated_duration_days: int
    cover_letter: str
    scope_references: tuple[str, ...]
    milestones: tuple[Milestone, ...]
    claims: tuple[Claim, ...]
    attachments: tuple[Attachment, ...]
    workflow_skill: str
    verifier_sha256: str
    payload_hash: str


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")


def _hash(label: str, value: Any) -> str:
    if not isinstance(value, str) or not _HASH.fullmatch(value):
        raise ProposalContractError(f"invalid_{label}")
    return value


def _text(label: str, value: Any, *, maximum: int = 10_000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or "\x00" in value:
        raise ProposalContractError(f"invalid_{label}")
    return value.strip()


def _positive(label: str, value: Any) -> int:
    if type(value) is not int or value < 1:
        raise ProposalContractError(f"invalid_{label}")
    return value


def _nonnegative(label: str, value: Any) -> int:
    if type(value) is not int or value < 0:
        raise ProposalContractError(f"invalid_{label}")
    return value


def _time(label: str, value: Any) -> datetime:
    text = _text(label, value, maximum=40)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProposalContractError(f"invalid_{label}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ProposalContractError(f"invalid_{label}")
    return parsed


def qualification_sha256(qualification: Qualification) -> str:
    if not isinstance(qualification, Qualification):
        raise ProposalContractError("invalid_qualification")
    return hashlib.sha256(_canonical(asdict(qualification))).hexdigest()


def _body(payload: ProposalPayload) -> dict[str, Any]:
    value = asdict(payload)
    value.pop("payload_hash")
    return value


def payload_sha256(payload: ProposalPayload) -> str:
    if not isinstance(payload, ProposalPayload):
        raise ProposalContractError("invalid_proposal_payload")
    return hashlib.sha256(_canonical(_body(payload))).hexdigest()


def _qualification_evidence(qualification: Qualification) -> dict[str, Any]:
    try:
        evidence = dict(qualification.evidence)
    except (TypeError, ValueError) as exc:
        raise ProposalContractError("invalid_qualification_evidence") from exc
    required = {
        "opportunity_source_hash", "skill_sha256", "verifier_sha256",
        "evaluated_at", "qualified_deadline_at", "active_project_count",
        "concurrent_job_cap",
    }
    if not required.issubset(evidence):
        raise ProposalContractError("invalid_qualification_evidence")
    return evidence


def build_proposal(
    *,
    opportunity: Any,
    qualification: Qualification,
    bid_minor: int,
    cover_letter: str,
    scope_references: tuple[str, ...],
    milestones: tuple[Milestone, ...],
    claims: tuple[Claim, ...],
    attachments: tuple[Attachment, ...],
    owner_assets: Mapping[str, str],
    estimated_duration_days: int,
) -> ProposalPayload:
    """Build a deterministic payload only; submission belongs to the effect fence."""
    if not isinstance(qualification, Qualification) or not qualification.eligible or qualification.risks:
        raise ProposalContractError("qualification_ineligible")
    evidence = _qualification_evidence(qualification)
    source_hash = _hash("opportunity_source_hash", getattr(opportunity, "source_hash", None))
    if evidence["opportunity_source_hash"] != source_hash:
        raise ProposalContractError("qualification_job_mismatch")
    verifier_hash = evidence["verifier_sha256"]
    if (
        not qualification.workflow.steps
        or qualification.workflow.verifier_skill == qualification.workflow.skill
        or not isinstance(verifier_hash, str) or not _HASH.fullmatch(verifier_hash)
    ):
        raise ProposalContractError("deliverability_unverified")

    title = _text("job_title", getattr(opportunity, "title", None), maximum=500)
    scope = _text("job_scope", getattr(opportunity, "scope", None))
    letter = _text("cover_letter", cover_letter, maximum=5000)
    title_terms = {term.casefold() for term in re.findall(r"[A-Za-z0-9]+", title) if len(term) >= 5}
    if len(title_terms.intersection(letter.casefold().split())) < min(2, len(title_terms)):
        raise ProposalContractError("generic_cover_letter")
    if not isinstance(scope_references, tuple) or not scope_references:
        raise ProposalContractError("scope_reference_required")
    source_text, letter_fold = f"{title}\n{scope}".casefold(), letter.casefold()
    normalized_references = tuple(_text("scope_reference", item, maximum=500) for item in scope_references)
    if any(item.casefold() not in source_text or item.casefold() not in letter_fold
           for item in normalized_references):
        raise ProposalContractError("scope_reference_unbound")

    bid = _positive("bid_minor", bid_minor)
    minimum = _positive("job_minimum_minor", getattr(opportunity, "minimum_minor", None))
    maximum = _positive("job_maximum_minor", getattr(opportunity, "maximum_minor", None))
    if not minimum <= bid <= maximum:
        raise ProposalContractError("bid_outside_job_bounds")
    pricing_kind = getattr(opportunity, "pricing_kind", None)
    if pricing_kind not in {"fixed", "hourly"}:
        raise ProposalContractError("invalid_pricing_kind")
    evaluated_at = _time("evaluated_at", evidence["evaluated_at"])
    deadline = _time("qualified_deadline_at", evidence["qualified_deadline_at"])
    duration = _positive("estimated_duration_days", estimated_duration_days)
    if evaluated_at >= deadline or duration * 86_400 > (deadline - evaluated_at).total_seconds():
        raise ProposalContractError("duration_outside_qualification")

    if not isinstance(milestones, tuple) or any(not isinstance(item, Milestone) for item in milestones):
        raise ProposalContractError("invalid_milestones")
    if pricing_kind == "fixed":
        if not milestones or sum(item.amount_minor for item in milestones) != bid:
            raise ProposalContractError("milestone_total_mismatch")
        for item in milestones:
            _text("milestone_title", item.title, maximum=200)
            _text("milestone_deliverable", item.deliverable, maximum=1000)
            if _positive("milestone_amount_minor", item.amount_minor) < 500:
                raise ProposalContractError("milestone_below_provider_minimum")
            due = _time("milestone_due_at", item.due_at)
            if due <= evaluated_at or due > deadline:
                raise ProposalContractError("milestone_outside_qualification")
    elif milestones:
        raise ProposalContractError("hourly_milestones_not_allowed")

    if not isinstance(owner_assets, Mapping) or not isinstance(claims, tuple):
        raise ProposalContractError("invalid_claims")
    for claim in claims:
        if not isinstance(claim, Claim):
            raise ProposalContractError("invalid_claims")
        text = _text("claim_text", claim.text, maximum=1000)
        evidence_id = _text("claim_evidence_id", claim.evidence_id, maximum=300)
        digest = _hash("claim_evidence_sha256", claim.evidence_sha256)
        if text.casefold() not in letter_fold or owner_assets.get(evidence_id) != digest:
            raise ProposalContractError("unsupported_claim")
    if not isinstance(attachments, tuple):
        raise ProposalContractError("invalid_attachments")
    for attachment in attachments:
        if not isinstance(attachment, Attachment):
            raise ProposalContractError("invalid_attachments")
        _text("attachment_name", attachment.name, maximum=300)
        evidence_id = _text("attachment_evidence_id", attachment.evidence_id, maximum=300)
        digest = _hash("attachment_content_sha256", attachment.content_sha256)
        if owner_assets.get(evidence_id) != digest:
            raise ProposalContractError("unsupported_attachment")

    unsealed = ProposalPayload(
        version=1,
        provider="upwork",
        opportunity_id=_text("opportunity_id", getattr(opportunity, "opportunity_id", None), maximum=100),
        opportunity_source_hash=source_hash,
        qualification_sha256=qualification_sha256(qualification),
        currency=_text("currency", getattr(opportunity, "currency", None), maximum=3),
        pricing_kind=pricing_kind,
        bid_minor=bid,
        connects_cost=_nonnegative("connects_cost", getattr(opportunity, "connects_cost", None)),
        estimated_duration_days=duration,
        cover_letter=letter,
        scope_references=normalized_references,
        milestones=milestones,
        claims=claims,
        attachments=attachments,
        workflow_skill=qualification.workflow.skill,
        verifier_sha256=verifier_hash,
        payload_hash="",
    )
    return ProposalPayload(**{**asdict(unsealed), "milestones": milestones, "claims": claims,
                              "attachments": attachments,
                              "payload_hash": hashlib.sha256(_canonical(_body(unsealed))).hexdigest()})
