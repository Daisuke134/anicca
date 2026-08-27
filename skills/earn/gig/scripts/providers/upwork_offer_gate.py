#!/usr/bin/env python3
"""Qualify one exact Upwork direct offer without accepting it."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from upwork_inbound_planner import InboundPlannerError, _object


HERE = Path(__file__).resolve()
GIG_ROOT = HERE.parents[2]
DEFAULT_RUNNER = GIG_ROOT.parents[2] / "runtime/agent-runner/agent_runner.py"
DEFAULT_SCHEMA = GIG_ROOT / "schemas/upwork_offer_decision.schema.json"
DEFAULT_PROFILE = Path.home() / ".config/anicca/job-search/profile.json"


def load_offer_packet(path: Path) -> dict[str, Any]:
    path = path.expanduser()
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o777 != 0o600:
        raise InboundPlannerError("offer_packet_not_private")
    packet = _object(path, "offer_packet")
    expected = {
        "version", "provider", "kind", "resource_id", "resource_url",
        "detail_evidence_sha256", "observed_at", "rendered_text",
    }
    canonical = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    url = urlsplit(str(packet.get("resource_url") or ""))
    if (
        set(packet) != expected or packet.get("version") != 1 or packet.get("provider") != "upwork"
        or packet.get("kind") != "direct_offer_detected"
        or not isinstance(packet.get("resource_id"), str) or not packet["resource_id"]
        or not re.fullmatch(r"[0-9a-f]{64}", str(packet.get("detail_evidence_sha256") or ""))
        or hashlib.sha256(canonical.encode()).hexdigest() != path.stem
        or url.scheme != "https" or url.netloc != "www.upwork.com"
        or packet["resource_id"] not in url.path
    ):
        raise InboundPlannerError("offer_packet_invalid")
    return packet


def planner_prompt(packet: dict[str, Any], owner_profile: dict[str, Any]) -> str:
    facts = json.dumps(owner_profile, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    inbound = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"""You qualify one Upwork direct offer. Return only schema-valid JSON.
Use only OWNER_PROFILE and OFFICIAL_OFFER. Never invent scope, price, deadline, funding, billing,
account state, identity, experience, availability, client facts, or requirements. Copy offer_id,
offer_url and offer_source_sha256 exactly. Choose accept only when the complete scope is feasible;
the amount/rate is explicit; the account visibly permits acceptance; no off-platform contact/payment
or synchronous/physical work is required; and payment protection is explicit. Fixed-price acceptance
requires a positive funded milestone. Hourly acceptance requires verified billing and a positive
weekly hour limit. If a material term is missing or negotiable, choose request_changes with exact
reason codes. Choose decline for infeasible, unsafe, deceptive, or prohibited work. A non-accept
action must set offer to null. Do not click or communicate.
OWNER_PROFILE={facts}
OFFICIAL_OFFER={inbound}"""


def validate_decision(decision: dict[str, Any], packet: dict[str, Any]) -> dict[str, Any]:
    if set(decision) != {"action", "reason_codes", "offer"}:
        raise InboundPlannerError("offer_decision_invalid")
    action = decision.get("action")
    reasons = decision.get("reason_codes")
    if (
        action not in {"accept", "request_changes", "decline"}
        or not isinstance(reasons, list)
        or any(not isinstance(item, str) or not item.strip() for item in reasons)
    ):
        raise InboundPlannerError("offer_decision_invalid")
    if action != "accept":
        if decision.get("offer") is not None or not reasons:
            raise InboundPlannerError("offer_decision_invalid")
        body = json.dumps(decision, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return {"action": action, "reason_codes": reasons, "offer": None,
                "decision_sha256": hashlib.sha256(body.encode()).hexdigest()}
    offer = decision.get("offer")
    expected = {
        "provider", "offer_id", "offer_url", "offer_source_sha256", "title", "scope",
        "contract_type", "rate_or_amount_usd", "deadline", "payment_protection",
        "funded_milestone_usd", "weekly_limit_hours", "account_state",
        "off_platform_required", "synchronous_or_physical_required",
    }
    if not isinstance(offer, dict) or set(offer) != expected:
        raise InboundPlannerError("offer_acceptance_mismatch")
    amount = offer.get("rate_or_amount_usd")
    deadline = offer.get("deadline")
    common_valid = (
        offer.get("provider") == "upwork"
        and offer.get("offer_id") == packet["resource_id"]
        and offer.get("offer_url") == packet["resource_url"]
        and offer.get("offer_source_sha256") == packet["detail_evidence_sha256"]
        and isinstance(offer.get("title"), str) and bool(offer["title"].strip())
        and isinstance(offer.get("scope"), str) and len(offer["scope"].strip()) >= 20
        and isinstance(amount, (int, float)) and not isinstance(amount, bool) and amount > 0
        and offer.get("account_state") == "accept_enabled"
        and offer.get("off_platform_required") is False
        and offer.get("synchronous_or_physical_required") is False
    )
    try:
        date.fromisoformat(deadline)
    except (TypeError, ValueError) as exc:
        raise InboundPlannerError("offer_acceptance_mismatch") from exc
    fixed_valid = (
        offer.get("contract_type") == "fixed_price"
        and offer.get("payment_protection") == "funded_milestone"
        and isinstance(offer.get("funded_milestone_usd"), (int, float))
        and not isinstance(offer.get("funded_milestone_usd"), bool)
        and offer["funded_milestone_usd"] > 0
        and offer["funded_milestone_usd"] >= amount
        and offer.get("weekly_limit_hours") is None
    )
    hourly_valid = (
        offer.get("contract_type") == "hourly"
        and offer.get("payment_protection") == "verified_hourly_billing"
        and offer.get("funded_milestone_usd") is None
        and type(offer.get("weekly_limit_hours")) is int
        and 1 <= offer["weekly_limit_hours"] <= 168
    )
    if not common_valid or not (fixed_valid or hourly_valid):
        raise InboundPlannerError("offer_acceptance_mismatch")
    body = json.dumps(decision, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {"action": "accept", "reason_codes": reasons, "offer": offer,
            "decision_sha256": hashlib.sha256(body.encode()).hexdigest()}


def invoke(
    packet_path: Path, *, runner: Path = DEFAULT_RUNNER, schema: Path = DEFAULT_SCHEMA,
    profile: Path = DEFAULT_PROFILE, evidence_dir: Path,
) -> dict[str, Any]:
    packet = load_offer_packet(packet_path)
    evidence_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(evidence_dir, 0o700)
    summary_path = evidence_dir / "summary.json"
    if not summary_path.is_file():
        completed = subprocess.run([
            sys.executable, str(runner), "--task-class", "application-intent-planner",
            "--prompt-stdin", "--schema", str(schema), "--evidence-dir", str(evidence_dir),
            "--task-label", "upwork-direct-offer-gate", "--loop", "gig-upwork",
            "--workdir", str(Path.home()), "--timeout-seconds", "420",
            "--escalation-reason", "client-facing Upwork direct offer terms qualification",
        ], input=planner_prompt(packet, _object(profile.expanduser(), "owner_profile")),
            text=True, capture_output=True, timeout=450, check=False)
        if completed.returncode != 0:
            raise InboundPlannerError("offer_planner_failed")
    summary = _object(summary_path, "offer_planner_summary")
    if summary.get("status") != "success":
        raise InboundPlannerError("offer_planner_failed")
    try:
        result = Path(str(summary["result_path"])).resolve()
        result.relative_to(evidence_dir.resolve())
    except (KeyError, OSError, ValueError) as exc:
        raise InboundPlannerError("offer_planner_result_unowned") from exc
    decision = validate_decision(_object(result, "offer_planner_result"), packet)
    for path in evidence_dir.rglob("*"):
        if path.is_file() and not path.is_symlink():
            os.chmod(path, 0o600)
    return decision
