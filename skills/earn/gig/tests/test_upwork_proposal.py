"""Contracts for immutable, evidence-bound Upwork proposal payloads."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


GIG_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = GIG_ROOT / "scripts"
PROVIDERS = SCRIPTS / "providers"
for directory in (SCRIPTS, PROVIDERS):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
from opportunity_qualifier import Qualification, Workflow  # noqa: E402
from upwork_adapter import UpworkOpportunity  # noqa: E402

MODULE = PROVIDERS / "upwork_proposal.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("upwork_proposal_test", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


proposal = _load_module() if MODULE.is_file() else None
NOW = datetime(2026, 8, 22, 10, tzinfo=timezone.utc)
DEADLINE = NOW + timedelta(days=3)


def _opportunity(**overrides: object):
    value = {
        "provider": "upwork",
        "opportunity_id": "~0123456789012345678",
        "source_hash": "a" * 64,
        "title": "Build a bounded Python ingestion adapter",
        "scope": "Normalize API records and verify idempotent pagination.",
        "currency": "USD",
        "pricing_kind": "fixed",
        "minimum_minor": 75_000,
        "maximum_minor": 100_000,
        "source_url": "https://www.upwork.com/jobs/Test_~0123456789012345678/",
        "observed_at": NOW.isoformat(),
        "skills": ("Python", "API"),
        "client_evidence": (("payment_verified", True),),
        "activity": (("applicants", 8),),
        "connects_cost": 10,
    }
    value.update(overrides)
    return UpworkOpportunity(**value)


def _qualification(**overrides: object) -> Qualification:
    workflow = Workflow(
        skill="builder", steps=("inspect scope", "build adapter", "run verifier"),
        deliverable="tested adapter", estimated_minutes=240, verifier_skill="judge",
    )
    evidence = (
        ("opportunity_source_hash", "a" * 64),
        ("skill_sha256", "1" * 64),
        ("verifier_sha256", "2" * 64),
        ("gross_minor", 90_000),
        ("active_project_count", 0),
        ("concurrent_job_cap", 3),
        ("evaluated_at", NOW.isoformat()),
        ("qualified_deadline_at", DEADLINE.isoformat()),
    )
    value = {
        "eligible": True, "workflow": workflow, "expected_net": 60_000,
        "risks": (), "evidence": evidence,
    }
    value.update(overrides)
    return Qualification(**value)


def _milestone(**overrides: object):
    assert proposal is not None, "upwork_proposal is not implemented"
    value = {
        "title": "Verified adapter delivery",
        "deliverable": "Python adapter, tests, and verification receipt",
        "due_at": (NOW + timedelta(days=2)).isoformat(),
        "amount_minor": 90_000,
    }
    value.update(overrides)
    return proposal.Milestone(**value)


def _build(**overrides: object):
    assert proposal is not None, "upwork_proposal is not implemented"
    arguments = {
        "opportunity": _opportunity(),
        "qualification": _qualification(),
        "bid_minor": 90_000,
        "cover_letter": (
            "I can build your bounded Python ingestion adapter. "
            "I will normalize API records and verify idempotent pagination. "
            "I can deliver a tested Python adapter."
        ),
        "scope_references": ("idempotent pagination",),
        "milestones": (_milestone(),),
        "claims": (proposal.Claim(
            text="I can deliver a tested Python adapter",
            evidence_id="verified_python_delivery",
            evidence_sha256="3" * 64,
        ),),
        "attachments": (proposal.Attachment(
            name="python-adapter-sample.pdf",
            evidence_id="python_adapter_sample",
            content_sha256="4" * 64,
        ),),
        "owner_assets": {
            "verified_python_delivery": "3" * 64,
            "python_adapter_sample": "4" * 64,
        },
        "estimated_duration_days": 2,
    }
    arguments.update(overrides)
    return proposal.build_proposal(**arguments)


def test_fixed_proposal_binds_job_qualification_terms_claims_and_hash():
    payload = _build()

    assert payload.provider == "upwork"
    assert payload.opportunity_id == "~0123456789012345678"
    assert payload.opportunity_source_hash == "a" * 64
    assert payload.bid_minor == 90_000
    assert payload.currency == "USD"
    assert payload.workflow_skill == "builder"
    assert payload.verifier_sha256 == "2" * 64
    assert payload.attachments[0].content_sha256 == "4" * 64
    assert payload.qualification_sha256 == proposal.qualification_sha256(_qualification())
    assert payload.payload_hash == proposal.payload_sha256(payload)
    assert _build() == payload
    with pytest.raises(FrozenInstanceError):
        payload.bid_minor = 1


def test_generic_copy_without_exact_job_title_is_rejected():
    with pytest.raises(proposal.ProposalContractError, match="generic_cover_letter"):
        _build(cover_letter="I am an experienced developer who can help with your project.")


def test_absent_scope_reference_is_rejected():
    with pytest.raises(proposal.ProposalContractError, match="scope_reference_required"):
        _build(scope_references=())


def test_scope_reference_must_exist_in_job_and_cover_letter():
    with pytest.raises(proposal.ProposalContractError, match="scope_reference_unbound"):
        _build(scope_references=("Kubernetes migration",))


def test_unsupported_profile_claim_is_rejected():
    unsupported = proposal.Claim(
        text="I served Fortune 500 clients", evidence_id="fortune_500",
        evidence_sha256="4" * 64,
    )
    with pytest.raises(proposal.ProposalContractError, match="unsupported_claim"):
        _build(claims=(unsupported,))


def test_attachment_must_be_a_factual_owner_asset():
    unsupported = proposal.Attachment(
        name="invented-case-study.pdf", evidence_id="invented_case_study",
        content_sha256="5" * 64,
    )
    with pytest.raises(proposal.ProposalContractError, match="unsupported_attachment"):
        _build(attachments=(unsupported,))


@pytest.mark.parametrize("bid", [74_999, 100_001])
def test_price_outside_observed_job_bounds_is_rejected(bid):
    with pytest.raises(proposal.ProposalContractError, match="bid_outside_job_bounds"):
        _build(bid_minor=bid, milestones=(_milestone(amount_minor=bid),))


def test_fixed_milestones_must_sum_to_bid_and_fit_qualified_deadline():
    with pytest.raises(proposal.ProposalContractError, match="milestone_total_mismatch"):
        _build(milestones=(_milestone(amount_minor=80_000),))
    with pytest.raises(proposal.ProposalContractError, match="milestone_outside_qualification"):
        _build(milestones=(_milestone(due_at=(DEADLINE + timedelta(seconds=1)).isoformat()),))


def test_missing_independent_delivery_verification_is_rejected():
    evidence = tuple(
        (key, None if key == "verifier_sha256" else value)
        for key, value in _qualification().evidence
    )
    with pytest.raises(proposal.ProposalContractError, match="deliverability_unverified"):
        _build(qualification=_qualification(evidence=evidence))


def test_ineligible_or_wrong_job_qualification_is_rejected():
    with pytest.raises(proposal.ProposalContractError, match="qualification_ineligible"):
        _build(qualification=_qualification(eligible=False, risks=("capacity_exhausted",)))
    wrong = tuple(
        (key, "f" * 64 if key == "opportunity_source_hash" else value)
        for key, value in _qualification().evidence
    )
    with pytest.raises(proposal.ProposalContractError, match="qualification_job_mismatch"):
        _build(qualification=_qualification(evidence=wrong))


def test_hourly_proposal_uses_rate_without_fixed_milestones():
    payload = _build(
        opportunity=_opportunity(
            pricing_kind="hourly", minimum_minor=5000, maximum_minor=7500,
        ),
        bid_minor=6000,
        milestones=(),
    )
    assert payload.pricing_kind == "hourly"
    assert payload.milestones == ()
