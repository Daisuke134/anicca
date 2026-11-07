"""G3 public-owned-host P0 read-only observation.

Reuse the existing published-site snapshot verifier and catalog candidate
selector instead of introducing a provider or authorization bypass.

This code reads ONLY the fixed, publicly available, company-owned
manager-support site. It does NOT access personal data or make external
writes. A candidate is REVIEW_ONLY until official source checks and a
separately authorized platform admission prove that an edit is permitted.

A real page read is NOT evidence of a model's human benefit, nor does it
complete the original P05-5 S1 model-vs-incumbent acceptance gate.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable

from .digital_environment import PAGES, validate_catalog, verify_readback
from .digital_handoff import PUBLIC_BASE
from .owned_catalog_planner import (
    _read_served_bundle,
    _potential_opportunity,
    find_current_page_opportunity,
)

SCHEMA = "manager.zero_ui.public_host_readonly.v1"
SOURCE_CATALOG = Path(__file__).resolve().parents[1] / "public_goods/service/catalog.json"


def _no_action(reason: str) -> dict:
    return {
        "schema": SCHEMA,
        "status": "NO_ACTION",
        "reason": reason,
        "world_action": "NO_ACTION",
        "external_writes": 0,
        "notifications_sent": 0,
        "personal_data_accessed": False,
        "human_benefit_measured": False,
        "full_s1_model_vs_incumbent_proven": False,
        "requires_ui_or_recurring_prompt": False,
    }


def run_public_host_shadow(
    *,
    enabled: bool = False,
    read_snapshot: Callable[[], tuple[dict, dict, bytes]] | None = None,
    catalog: dict | None = None,
    observed_at: datetime | None = None,
) -> dict:
    """Observe public host, compare current NO_ACTION with a fixed rule candidate.

    The only real network GET comes from _read_served_bundle(), already fixed to
    the owned public site in existing Manager code. Caller cannot pass a URL.
    Zero external writes, model training, notification, or identity collection.
    """
    if type(enabled) is not bool:
        raise ValueError("enabled requires exact boolean")
    if not enabled:
        return _no_action("DISABLED")
    at = observed_at or datetime.now(timezone.utc)
    if not isinstance(at, datetime) or at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("timezone-aware observation required")
    if catalog is None:
        catalog = json.loads(SOURCE_CATALOG.read_text(encoding="utf-8"))
    validate_catalog(catalog)

    snapshot_reader = _read_served_bundle if read_snapshot is None else read_snapshot
    if not callable(snapshot_reader):
        raise ValueError("snapshot reader required")
    manifest, bodies, raw_manifest = snapshot_reader()
    if type(raw_manifest) is not bytes or len(raw_manifest) > 1024 * 128:
        raise ValueError("invalid manifest bytes")
    try:
        decoded = json.loads(raw_manifest.decode("utf-8"))
    except (ValueError, UnicodeError):
        raise ValueError("invalid raw manifest") from None
    if decoded != manifest:
        raise ValueError("raw manifest and verified bundle differ")
    receipt = verify_readback(manifest, bodies)

    legacy = _potential_opportunity(bodies, catalog)
    other = None if legacy is not None else find_current_page_opportunity(bodies)
    opportunity = legacy if legacy is not None else other
    snap_sha = sha256(raw_manifest).hexdigest()
    candidate_decision = "REVIEW_ONLY" if opportunity is not None else "NO_ACTION"
    candidate = {
        "decision": candidate_decision,
        "context_sha256": snap_sha,
        "authorized_execution": False,
        "rule": "existing_manager_owned_catalog_planner",
        "human_model_forward_pass": False,
    }
    if opportunity is not None:
        candidate["proposed_action"] = opportunity.action
        candidate["target_path"] = opportunity.target_path

    return {
        **_no_action("PUBLIC_HOST_READBACK_ONLY"),
        "status": "PUBLIC_HOST_READONLY_VERIFIED",
        "public_source_url": PUBLIC_BASE,
        "observed_at": at.isoformat(),
        "page_count": len(bodies),
        "source_commit": manifest["source_commit"],
        "public_manifest_sha256": snap_sha,
        "technical_proof": receipt["technical_proof"],
        "baseline": {"decision": "NO_ACTION", "context_sha256": snap_sha},
        "candidate": candidate,
        "outcome": "NOT_MEASURED",
        "real_world_provider_admission": False,
    }
