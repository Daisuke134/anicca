#!/usr/bin/env python3
"""Turn one private actionable Upwork inbound packet into a sealed proposal."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


HERE = Path(__file__).resolve()
GIG_ROOT = HERE.parents[2]
REPO_ROOT = HERE.parents[5]
SCRIPTS = GIG_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from storefront_bootstrap import inventory as capability_inventory  # noqa: E402

DEFAULT_RUNNER = GIG_ROOT / "agent-runner/agent_runner.py"
DEFAULT_SCHEMA = GIG_ROOT / "schemas/upwork_inbound_proposal.schema.json"
DEFAULT_PROFILE = Path.home() / ".config/anicca/job-search/profile.json"


class InboundPlannerError(ValueError):
    """A model decision cannot be bound to the exact private inbound."""


def _object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InboundPlannerError(f"{label}_unreadable") from exc
    if not isinstance(value, dict):
        raise InboundPlannerError(f"{label}_invalid")
    return value


def load_packet(path: Path) -> dict[str, Any]:
    path = path.expanduser()
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o777 != 0o600:
        raise InboundPlannerError("inbound_packet_not_private")
    packet = _object(path, "inbound_packet")
    expected = {
        "version", "provider", "kind", "resource_id", "resource_url",
        "detail_evidence_sha256", "observed_at", "rendered_text",
    }
    kind = packet.get("kind")
    if kind == "public_job":
        expected |= {"required_connects", "available_connects_before"}
    canonical = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    if (
        set(packet) != expected or packet.get("version") != 1 or packet.get("provider") != "upwork"
        or kind not in {"invitation_detected", "public_job"}
        or not isinstance(packet.get("resource_id"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", str(packet.get("detail_evidence_sha256") or ""))
        or hashlib.sha256(canonical.encode()).hexdigest() != path.stem
        or (kind == "public_job" and (
            type(packet.get("required_connects")) is not int
            or type(packet.get("available_connects_before")) is not int
            or packet["required_connects"] < 0
            or packet["available_connects_before"] < packet["required_connects"]
        ))
    ):
        raise InboundPlannerError("inbound_packet_invalid")
    url = urlsplit(str(packet.get("resource_url") or ""))
    if url.scheme != "https" or url.netloc != "www.upwork.com" or packet["resource_id"] not in url.path:
        raise InboundPlannerError("inbound_packet_invalid")
    return packet


def planner_prompt(
    packet: dict[str, Any], owner_profile: dict[str, Any], capabilities: dict[str, Any],
) -> str:
    facts = json.dumps(owner_profile, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    inbound = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    skills = json.dumps(capabilities, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    required = packet.get("required_connects", 0)
    available = packet.get("available_connects_before", 0)
    status = "frozen_waiting_for_connects" if packet.get("kind") == "public_job" else "frozen_waiting_for_invitation"
    return f"""You decide one Upwork proposal. Return only schema-valid JSON.
Use only facts present in OWNER_PROFILE and OFFICIAL_INBOUND. Never invent experience, identity,
availability, credentials, portfolio, results, client facts, requirements, questions, price, or scope.
Choose skip when delivery is not fully feasible, required facts are missing, synchronous/physical work
is required, the client requests off-platform contact/payment, or exact questions cannot be answered.
Installed Skills are executable delivery capabilities, not claims of prior client experience. Do not
invent experience, but do not skip solely because an exact prior job, testimonial or portfolio item is
absent when the work can be completed and independently verified with an installed Skill. Missing
pre-contract implementation details may become concise client questions rather than automatic rejection.
For submit, copy job_id, job_url and job_source_sha256 exactly; status is {status}, required_connects
is {required}, available_connects_before is {available}; unsupported_claims and attachments are empty. Keep all
pre-contract communication on Upwork. The proposal must be specific, concise, truthful, and answer
every explicit screening question exactly once.
OWNER_PROFILE={facts}
INSTALLED_SKILLS={skills}
OFFICIAL_INBOUND={inbound}"""


def validate_decision(
    decision: dict[str, Any], packet: dict[str, Any],
) -> dict[str, Any] | None:
    if set(decision) != {"decision", "reason_codes", "proposal"}:
        raise InboundPlannerError("inbound_decision_invalid")
    reasons = decision.get("reason_codes")
    if not isinstance(reasons, list) or any(not isinstance(item, str) or not item for item in reasons):
        raise InboundPlannerError("inbound_decision_invalid")
    if decision.get("decision") == "skip":
        if decision.get("proposal") is not None or not reasons:
            raise InboundPlannerError("inbound_decision_invalid")
        return None
    proposal = decision.get("proposal")
    if decision.get("decision") != "submit" or not isinstance(proposal, dict):
        raise InboundPlannerError("inbound_decision_invalid")
    expected_keys = {
        "provider", "job_id", "job_url", "job_source_sha256", "title", "status",
        "terms", "cover_letter", "screening_answers", "unsupported_claims", "attachments",
    }
    terms = proposal.get("terms")
    answers = proposal.get("screening_answers")
    url = urlsplit(str(proposal.get("job_url") or ""))
    is_public = packet.get("kind") == "public_job"
    expected_status = "frozen_waiting_for_connects" if is_public else "frozen_waiting_for_invitation"
    expected_required = packet.get("required_connects", 0)
    expected_available = packet.get("available_connects_before", 0)
    if (
        set(proposal) != expected_keys or proposal.get("provider") != "upwork"
        or proposal.get("job_id") != packet["resource_id"]
        or proposal.get("job_url") != packet["resource_url"]
        or proposal.get("job_source_sha256") != packet["detail_evidence_sha256"]
        or proposal.get("status") != expected_status
        or url.scheme != "https" or url.netloc != "www.upwork.com"
        or not isinstance(proposal.get("title"), str) or not proposal["title"].strip()
        or not isinstance(proposal.get("cover_letter"), str) or len(proposal["cover_letter"].strip()) < 80
        or not isinstance(terms, dict) or set(terms) != {
            "type", "bid_usd", "delivery_days", "required_connects", "available_connects_before",
        }
        or terms.get("type") not in {"fixed_price", "hourly"}
        or not isinstance(terms.get("bid_usd"), (int, float)) or isinstance(terms.get("bid_usd"), bool)
        or terms["bid_usd"] <= 0
        or type(terms.get("delivery_days")) is not int or not 1 <= terms["delivery_days"] <= 365
        or terms.get("required_connects") != expected_required
        or terms.get("available_connects_before") != expected_available
        or not isinstance(answers, list)
        or any(
            not isinstance(answer, dict) or set(answer) != {"question", "answer"}
            or not all(isinstance(answer[key], str) and answer[key].strip() for key in answer)
            for answer in answers
        )
        or proposal.get("unsupported_claims") != [] or proposal.get("attachments") != []
    ):
        raise InboundPlannerError("inbound_decision_mismatch")
    body = json.dumps(proposal, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    return {**proposal, "payload_sha256": hashlib.sha256(body.encode()).hexdigest()}


def invoke(
    packet_path: Path, *, runner: Path = DEFAULT_RUNNER, schema: Path = DEFAULT_SCHEMA,
    profile: Path = DEFAULT_PROFILE, evidence_dir: Path,
) -> dict[str, Any] | None:
    packet = load_packet(packet_path)
    evidence_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(evidence_dir, 0o700)
    summary_path = evidence_dir / "summary.json"
    if not summary_path.is_file():
        prompt = planner_prompt(
            packet, _object(profile.expanduser(), "owner_profile"), capability_inventory(REPO_ROOT),
        )
        completed = subprocess.run([
            sys.executable, str(runner), "--task-class", "application-intent-planner",
            "--prompt-stdin", "--schema", str(schema), "--evidence-dir", str(evidence_dir),
            "--task-label", "upwork-inbound-proposal", "--loop", "gig-upwork",
            "--workdir", str(Path.home()), "--timeout-seconds", "420",
            "--escalation-reason", "client-facing zero-Connect Upwork invitation proposal",
        ], input=prompt, text=True, capture_output=True, timeout=450, check=False)
        if completed.returncode != 0:
            raise InboundPlannerError("inbound_planner_failed")
    summary = _object(summary_path, "planner_summary")
    if summary.get("status") != "success":
        raise InboundPlannerError("inbound_planner_failed")
    try:
        result = Path(str(summary["result_path"])).resolve()
        result.relative_to(evidence_dir.resolve())
    except (KeyError, OSError, ValueError) as exc:
        raise InboundPlannerError("inbound_planner_result_unowned") from exc
    proposal = validate_decision(_object(result, "planner_result"), packet)
    for path in evidence_dir.rglob("*"):
        if path.is_file() and not path.is_symlink():
            os.chmod(path, 0o600)
    return proposal


def write_sealed_proposal(proposal: dict[str, Any], root: Path) -> Path:
    """Persist only a mechanically validated submit decision for the browser effect."""
    digest = proposal.get("payload_sha256") if isinstance(proposal, dict) else None
    job_id = proposal.get("job_id") if isinstance(proposal, dict) else None
    if (
        not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
        or not isinstance(job_id, str) or not job_id
    ):
        raise InboundPlannerError("sealed_inbound_proposal_invalid")
    root = root.expanduser()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    path = root / f"{hashlib.sha256(job_id.encode()).hexdigest()}.json"
    body = json.dumps(proposal, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != body:
        raise InboundPlannerError("sealed_inbound_proposal_immutable")
    if not path.exists():
        path.write_text(body, encoding="utf-8")
    os.chmod(path, 0o600)
    return path
