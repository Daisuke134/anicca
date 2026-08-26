"""Contracts for provider-neutral, evidence-bound opportunity qualification."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
MODULE = SCRIPTS / "opportunity_qualifier.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("opportunity_qualifier_test", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


qualifier = _load_module() if MODULE.is_file() else None
NOW = datetime(2026, 8, 22, 10, tzinfo=timezone.utc)


def _private_json(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    os.chmod(path, 0o600)
    return path


def _facts(tmp_path: Path, *, cap: int = 3, skills: tuple[str, ...] = ("builder", "judge")):
    inventory = _private_json(tmp_path / "inventory.json", {
        "version": 1,
        "probe_mode": "read_only",
        "marketplace_mutations": 0,
        "skills": [{"skill": skill, "source_sha256": str(index + 1) * 64,
                    "capabilities": [f"{skill}_capability"]}
                   for index, skill in enumerate(skills)],
    })
    owner = _private_json(tmp_path / "owner.json", {
        "version": 1,
        "bounds": {
            "minimum_margin_bps": 2500,
            "concurrent_job_cap": cap,
            "human_minute_value_minor": 75,
        },
        "portfolio_assets": ["verified_python_delivery"],
    })
    projects = tmp_path / "projects"
    projects.mkdir()
    return inventory, owner, projects


def _opportunity(**overrides: object):
    value = {
        "provider": "upwork",
        "opportunity_id": "job-1",
        "source_hash": "a" * 64,
        "pricing_kind": "fixed",
        "minimum_minor": 100_000,
        "connects_cost": 10,
    }
    value.update(overrides)
    return SimpleNamespace(**value)


def _workflow(**overrides: object):
    assert qualifier is not None, "opportunity_qualifier is not implemented"
    value = {
        "skill": "builder",
        "steps": ("inspect scope", "build artifact", "run checks"),
        "deliverable": "tested artifact",
        "estimated_minutes": 60,
        "verifier_skill": "judge",
        "required_claims": (),
    }
    value.update(overrides)
    return qualifier.Workflow(**value)


def _qualify(tmp_path: Path, **overrides: object):
    inventory, owner, projects = _facts(
        tmp_path, cap=int(overrides.pop("cap", 3)),
        skills=overrides.pop("skills", ("builder", "judge")),
    )
    arguments = {
        "opportunity": _opportunity(),
        "workflow": _workflow(),
        "inventory_path": inventory,
        "owner_profile_path": owner,
        "projects_root": projects,
        "now": NOW,
        "deadline_at": NOW + timedelta(hours=4),
        "fee_bps": 1000,
        "connects_unit_cost_minor": 15,
        "tool_cost_minor": 1000,
        "risk_reserve_minor": 5000,
    }
    arguments.update(overrides)
    return qualifier.qualify(**arguments)


def test_eligible_fixed_job_has_conservative_net_and_evidence(tmp_path):
    result = _qualify(tmp_path)

    assert result.eligible is True
    assert result.workflow.skill == "builder"
    assert result.expected_net == 79_350
    assert result.risks == ()
    assert dict(result.evidence)["gross_minor"] == 100_000
    assert dict(result.evidence)["skill_sha256"] == "1" * 64
    assert dict(result.evidence)["verifier_sha256"] == "2" * 64
    assert dict(result.evidence)["evaluated_at"] == NOW.isoformat()
    assert dict(result.evidence)["qualified_deadline_at"] == (
        NOW + timedelta(hours=4)
    ).isoformat()
    assert dict(result.evidence)["concurrent_job_cap"] == 3


def test_profile_without_connects_cap_can_qualify_positive_job(tmp_path):
    inventory, owner, projects = _facts(tmp_path)

    result = qualifier.qualify(
        _opportunity(), _workflow(), inventory_path=inventory,
        owner_profile_path=owner, projects_root=projects, now=NOW,
        deadline_at=NOW + timedelta(hours=4), fee_bps=1000,
        connects_unit_cost_minor=15, tool_cost_minor=1000, risk_reserve_minor=5000,
    )

    assert result.eligible is True
    assert result.expected_net > 0
    assert "connects_cap_exceeded" not in result.risks


def test_missing_installed_skill_is_ineligible(tmp_path):
    result = _qualify(tmp_path, skills=("judge",))
    assert result.eligible is False
    assert "missing_skill" in result.risks


def test_impossible_deadline_is_ineligible(tmp_path):
    result = _qualify(tmp_path, deadline_at=NOW + timedelta(minutes=59))
    assert result.eligible is False
    assert "impossible_deadline" in result.risks


def test_current_paid_project_capacity_is_enforced(tmp_path):
    inventory, owner, projects = _facts(tmp_path, cap=1)
    project = projects / "paid-1"
    project.mkdir()
    (project / "state.json").write_text(json.dumps({
        "provider": "upwork", "project_status": "active", "updated_at": NOW.isoformat(),
    }), encoding="utf-8")

    result = qualifier.qualify(
        _opportunity(), _workflow(), inventory_path=inventory,
        owner_profile_path=owner, projects_root=projects, now=NOW,
        deadline_at=NOW + timedelta(hours=4), fee_bps=1000,
        connects_unit_cost_minor=15, tool_cost_minor=1000, risk_reserve_minor=5000,
    )
    assert result.eligible is False
    assert "capacity_exhausted" in result.risks


def test_unix_second_project_timestamp_is_current_capacity_evidence(tmp_path):
    inventory, owner, projects = _facts(tmp_path, cap=1)
    project = projects / "paid-unix-seconds"
    project.mkdir()
    (project / "state.json").write_text(json.dumps({
        "provider": "upwork", "project_status": "active", "updated_at": NOW.timestamp(),
    }), encoding="utf-8")
    result = qualifier.qualify(
        _opportunity(), _workflow(), inventory_path=inventory,
        owner_profile_path=owner, projects_root=projects, now=NOW,
        deadline_at=NOW + timedelta(hours=4), fee_bps=1000,
        connects_unit_cost_minor=15, tool_cost_minor=1000, risk_reserve_minor=5000,
    )
    assert "capacity_exhausted" in result.risks
    assert "unknown_capacity" not in result.risks
    assert dict(result.evidence)["active_project_count"] == 1


def test_negative_expected_net_is_never_eligible(tmp_path):
    result = _qualify(
        tmp_path, opportunity=_opportunity(minimum_minor=1000),
        tool_cost_minor=2000, risk_reserve_minor=1000,
    )
    assert result.expected_net < 0
    assert result.eligible is False
    assert "negative_expected_net" in result.risks


def test_deliverable_requires_a_different_installed_verifier(tmp_path):
    result = _qualify(tmp_path, workflow=_workflow(verifier_skill="builder"))
    assert result.eligible is False
    assert "unverifiable_deliverable" in result.risks


def test_profile_claim_must_be_backed_by_private_owner_evidence(tmp_path):
    result = _qualify(tmp_path, workflow=_workflow(required_claims=("fortune_500_client",)))
    assert result.eligible is False
    assert "false_profile_claim" in result.risks


def test_hourly_rate_is_prorated_to_workflow_duration(tmp_path):
    result = _qualify(
        tmp_path, opportunity=_opportunity(pricing_kind="hourly", minimum_minor=6000),
    )
    assert dict(result.evidence)["gross_minor"] == 6000


def test_stale_active_capacity_is_unknown_not_silently_free(tmp_path):
    inventory, owner, projects = _facts(tmp_path)
    project = projects / "stale-paid"
    project.mkdir()
    (project / "state.json").write_text(json.dumps({
        "provider": "upwork", "project_status": "active",
        "updated_at": (NOW - timedelta(days=8)).isoformat(),
    }), encoding="utf-8")
    result = qualifier.qualify(
        _opportunity(), _workflow(), inventory_path=inventory,
        owner_profile_path=owner, projects_root=projects, now=NOW,
        deadline_at=NOW + timedelta(hours=4), fee_bps=1000,
        connects_unit_cost_minor=15, tool_cost_minor=1000, risk_reserve_minor=5000,
    )
    assert result.eligible is False
    assert "unknown_capacity" in result.risks


def test_coconala_project_never_consumes_upwork_capacity(tmp_path):
    inventory, owner, projects = _facts(tmp_path, cap=1)
    project = projects / "coconala-paid"
    project.mkdir()
    (project / "state.json").write_text(json.dumps({
        "provider": "coconala", "talkroom_state": "取引中",
        "updated_at": NOW.isoformat(),
    }), encoding="utf-8")

    result = qualifier.qualify(
        _opportunity(), _workflow(), inventory_path=inventory,
        owner_profile_path=owner, projects_root=projects, now=NOW,
        deadline_at=NOW + timedelta(hours=4), fee_bps=1000,
        connects_unit_cost_minor=15, tool_cost_minor=1000, risk_reserve_minor=5000,
    )

    assert result.eligible is True
    assert dict(result.evidence)["active_project_count"] == 0


def test_missing_provider_project_never_consumes_upwork_capacity(tmp_path):
    inventory, owner, projects = _facts(tmp_path, cap=1)
    project = projects / "legacy-coconala-paid"
    project.mkdir()
    (project / "state.json").write_text(json.dumps({
        "talkroom_state": "取引中", "updated_at": NOW.isoformat(),
    }), encoding="utf-8")

    result = qualifier.qualify(
        _opportunity(), _workflow(), inventory_path=inventory,
        owner_profile_path=owner, projects_root=projects, now=NOW,
        deadline_at=NOW + timedelta(hours=4), fee_bps=1000,
        connects_unit_cost_minor=15, tool_cost_minor=1000, risk_reserve_minor=5000,
    )

    assert result.eligible is True
    assert dict(result.evidence)["active_project_count"] == 0


def test_builder_and_verifier_capabilities_must_match_workflow(tmp_path):
    result = _qualify(tmp_path, workflow=_workflow(
        required_capabilities=("multi_tenant_api",),
        verification_capabilities=("tenant_isolation_contract",),
    ))
    assert result.eligible is False
    assert "capability_mismatch" in result.risks
    assert "verification_capability_mismatch" in result.risks


def test_opportunity_requires_upwork_provider_and_sha256_source_evidence(tmp_path):
    (tmp_path / "provider").mkdir()
    (tmp_path / "hash").mkdir()
    with pytest.raises(qualifier.QualificationContractError, match="invalid_opportunity_evidence"):
        _qualify(tmp_path / "provider", opportunity=_opportunity(provider="coconala"))
    with pytest.raises(qualifier.QualificationContractError, match="invalid_opportunity_evidence"):
        _qualify(tmp_path / "hash", opportunity=_opportunity(source_hash=None))


def test_private_fact_files_must_not_be_world_readable(tmp_path):
    inventory, owner, projects = _facts(tmp_path)
    os.chmod(inventory, 0o644)
    with pytest.raises(qualifier.QualificationContractError, match="unsafe_private_file"):
        qualifier.qualify(
            _opportunity(), _workflow(), inventory_path=inventory,
            owner_profile_path=owner, projects_root=projects, now=NOW,
            deadline_at=NOW + timedelta(hours=4), fee_bps=1000,
            connects_unit_cost_minor=15, tool_cost_minor=1000, risk_reserve_minor=5000,
        )
