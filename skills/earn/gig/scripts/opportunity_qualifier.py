#!/usr/bin/env python3
"""Provider-neutral opportunity qualification from private, observed facts."""

from __future__ import annotations

import json
import re
import stat
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


class QualificationContractError(ValueError):
    """Raised when qualification inputs cannot be trusted."""


@dataclass(frozen=True)
class Workflow:
    skill: str
    steps: tuple[str, ...]
    deliverable: str
    estimated_minutes: int
    verifier_skill: str
    required_claims: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    verification_capabilities: tuple[str, ...] = ()


@dataclass(frozen=True)
class Qualification:
    eligible: bool
    workflow: Workflow
    expected_net: int
    risks: tuple[str, ...]
    evidence: tuple[tuple[str, Any], ...]


def _private_json(path: Path) -> dict[str, Any]:
    path = Path(path)
    if stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise QualificationContractError(f"unsafe_private_file:{path.name}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QualificationContractError(f"invalid_private_file:{path.name}") from exc
    if not isinstance(value, dict):
        raise QualificationContractError(f"invalid_private_file:{path.name}")
    return value


def _integer(name: str, value: Any, *, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise QualificationContractError(f"invalid_{name}")
    if maximum is not None and value > maximum:
        raise QualificationContractError(f"invalid_{name}")
    return value


def _aware(name: str, value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise QualificationContractError(f"invalid_{name}")
    return value


def _installed_skills(inventory: dict[str, Any]) -> dict[str, tuple[str, frozenset[str]]]:
    if inventory.get("probe_mode") != "read_only" or inventory.get("marketplace_mutations") != 0:
        raise QualificationContractError("untrusted_skill_inventory")
    rows = inventory.get("skills")
    if not isinstance(rows, list):
        raise QualificationContractError("invalid_skill_inventory")
    installed: dict[str, tuple[str, frozenset[str]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise QualificationContractError("invalid_skill_inventory")
        name, digest = row.get("skill"), row.get("source_sha256")
        if not isinstance(name, str) or not name or not isinstance(digest, str) or len(digest) != 64:
            raise QualificationContractError("invalid_skill_inventory")
        capabilities = row.get("capabilities", [])
        if not isinstance(capabilities, list) or any(
            not isinstance(item, str) or not item.strip() for item in capabilities
        ):
            raise QualificationContractError("invalid_skill_inventory")
        installed[name] = (digest, frozenset(capabilities))
    return installed


def _capacity(projects_root: Path, now: datetime) -> tuple[int, bool]:
    active = 0
    stale_active = False
    if not Path(projects_root).is_dir():
        raise QualificationContractError("missing_projects_root")
    for path in sorted(Path(projects_root).glob("*/state.json")):
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise QualificationContractError(f"invalid_project_state:{path.parent.name}") from exc
        if not isinstance(state, dict):
            raise QualificationContractError(f"invalid_project_state:{path.parent.name}")
        if state.get("provider") != "upwork":
            continue
        is_active = state.get("talkroom_state") == "取引中" or state.get("project_status") in {
            "active", "accepted", "in_progress",
        }
        if not is_active:
            continue
        raw_updated = state.get("updated_at")
        try:
            if isinstance(raw_updated, (int, float)) and not isinstance(raw_updated, bool):
                updated = datetime.fromtimestamp(raw_updated, tz=now.tzinfo)
            else:
                updated = datetime.fromisoformat(str(raw_updated).replace("Z", "+00:00"))
        except (ValueError, OSError, OverflowError):
            stale_active = True
            continue
        if updated.tzinfo is None or updated.utcoffset() is None or updated > now:
            stale_active = True
        elif now - updated > timedelta(days=7):
            stale_active = True
        else:
            active += 1
    return active, stale_active


def qualify(
    opportunity: Any,
    workflow: Workflow,
    *,
    inventory_path: Path,
    owner_profile_path: Path,
    projects_root: Path,
    now: datetime,
    deadline_at: datetime,
    fee_bps: int,
    connects_unit_cost_minor: int,
    tool_cost_minor: int,
    risk_reserve_minor: int,
) -> Qualification:
    """Return a conservative qualification without creating marketplace effects."""
    now, deadline_at = _aware("now", now), _aware("deadline_at", deadline_at)
    inventory = _private_json(inventory_path)
    owner = _private_json(owner_profile_path)
    installed = _installed_skills(inventory)
    bounds = owner.get("bounds")
    if not isinstance(bounds, dict):
        raise QualificationContractError("invalid_owner_bounds")

    fee_bps = _integer("fee_bps", fee_bps, maximum=10_000)
    connects_unit_cost_minor = _integer("connects_unit_cost_minor", connects_unit_cost_minor)
    tool_cost_minor = _integer("tool_cost_minor", tool_cost_minor)
    risk_reserve_minor = _integer("risk_reserve_minor", risk_reserve_minor)
    minimum_margin_bps = _integer(
        "minimum_margin_bps", bounds.get("minimum_margin_bps"), maximum=10_000,
    )
    capacity_cap = _integer("concurrent_job_cap", bounds.get("concurrent_job_cap"))
    human_minute_value = _integer(
        "human_minute_value_minor", bounds.get("human_minute_value_minor"),
    )
    minutes = _integer("estimated_minutes", workflow.estimated_minutes)
    if minutes == 0:
        raise QualificationContractError("invalid_estimated_minutes")

    minimum_minor = _integer("minimum_minor", getattr(opportunity, "minimum_minor", None))
    connects = _integer("connects_cost", getattr(opportunity, "connects_cost", None))
    source_hash = getattr(opportunity, "source_hash", None)
    if (
        getattr(opportunity, "provider", None) != "upwork"
        or not isinstance(source_hash, str)
        or re.fullmatch(r"[0-9a-f]{64}", source_hash) is None
    ):
        raise QualificationContractError("invalid_opportunity_evidence")
    pricing_kind = getattr(opportunity, "pricing_kind", None)
    if pricing_kind == "fixed":
        gross = minimum_minor
    elif pricing_kind == "hourly":
        gross = minimum_minor * minutes // 60
    else:
        raise QualificationContractError("invalid_pricing_kind")

    fee = (gross * fee_bps + 9_999) // 10_000
    connects_cost = connects * connects_unit_cost_minor
    labor_cost = minutes * human_minute_value
    expected_net = gross - fee - connects_cost - tool_cost_minor - risk_reserve_minor - labor_cost
    active_count, stale_active = _capacity(projects_root, now)
    risks: list[str] = []
    builder = installed.get(workflow.skill)
    if builder is None:
        risks.append("missing_skill")
    elif not set(workflow.required_capabilities).issubset(builder[1]):
        risks.append("capability_mismatch")
    if deadline_at < now + timedelta(minutes=minutes):
        risks.append("impossible_deadline")
    if active_count >= capacity_cap:
        risks.append("capacity_exhausted")
    if stale_active:
        risks.append("unknown_capacity")
    if expected_net < 0:
        risks.append("negative_expected_net")
    elif gross == 0 or expected_net * 10_000 < gross * minimum_margin_bps:
        risks.append("below_minimum_margin")
    verifier = installed.get(workflow.verifier_skill)
    verifier_hash = verifier[0] if verifier else None
    if (
        not workflow.steps or any(not isinstance(step, str) or not step.strip() for step in workflow.steps)
        or not isinstance(workflow.deliverable, str) or not workflow.deliverable.strip()
        or workflow.verifier_skill == workflow.skill or verifier_hash is None
    ):
        risks.append("unverifiable_deliverable")
    elif not set(workflow.verification_capabilities).issubset(verifier[1]):
        risks.append("verification_capability_mismatch")
    assets = owner.get("portfolio_assets")
    if not isinstance(assets, list) or not set(workflow.required_claims).issubset(set(assets)):
        risks.append("false_profile_claim")

    evidence: tuple[tuple[str, Any], ...] = (
        ("opportunity_source_hash", source_hash),
        ("skill_sha256", builder[0] if builder else None),
        ("verifier_sha256", verifier_hash),
        ("gross_minor", gross),
        ("fee_minor", fee),
        ("connects_cost_minor", connects_cost),
        ("tool_cost_minor", tool_cost_minor),
        ("risk_reserve_minor", risk_reserve_minor),
        ("labor_cost_minor", labor_cost),
        ("active_project_count", active_count),
        ("concurrent_job_cap", capacity_cap),
        ("evaluated_at", now.isoformat()),
        ("qualified_deadline_at", deadline_at.isoformat()),
    )
    return Qualification(not risks, workflow, expected_net, tuple(risks), evidence)
