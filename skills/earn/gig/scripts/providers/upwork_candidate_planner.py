#!/usr/bin/env python3
"""Model-qualify one official Upwork job and seal a truthful public proposal."""

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
DEFAULT_RUNNER = GIG_ROOT / "agent-runner/agent_runner.py"
DEFAULT_SCHEMA = GIG_ROOT / "schemas/upwork_public_proposal.schema.json"
DEFAULT_PROFILE = Path.home() / ".config/anicca/job-search/profile.json"


class CandidatePlannerError(ValueError):
    """A public-job decision is not bound to its official evidence."""


def _object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidatePlannerError(f"{label}_unreadable") from exc
    if not isinstance(value, dict):
        raise CandidatePlannerError(f"{label}_invalid")
    return value


def write_packet(
    *, job_id: str, job_url: str, title: str, rendered_text: str,
    evidence_sha256: str, connects_required: int, available_connects: int,
    observed_at: str, skill_files: list[Path], root: Path,
) -> Path:
    url = urlsplit(job_url)
    if (
        not re.fullmatch(r"~\d{15,}", job_id) or url.scheme != "https"
        or url.netloc != "www.upwork.com" or job_id not in url.path
        or not title.strip() or not rendered_text.strip()
        or not re.fullmatch(r"[0-9a-f]{64}", evidence_sha256)
        or type(connects_required) is not int or connects_required < 0
        or type(available_connects) is not int or available_connects < 0
    ):
        raise CandidatePlannerError("public_job_packet_invalid")
    skills = []
    for path in skill_files:
        if path.is_file() and not path.is_symlink():
            skills.append({
                "path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "contract": path.read_text(encoding="utf-8")[:30000],
            })
    if not skills:
        raise CandidatePlannerError("public_job_skills_missing")
    packet = {
        "version": 1, "provider": "upwork", "kind": "public_job",
        "job_id": job_id, "job_url": job_url, "title": title.strip(),
        "detail_evidence_sha256": evidence_sha256,
        "connects_required": connects_required,
        "available_connects_before": available_connects,
        "observed_at": observed_at, "rendered_text": rendered_text[:60000],
        "installed_skills": skills,
    }
    body = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    root = root.expanduser()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    path = root / f"{hashlib.sha256(body.encode()).hexdigest()}.json"
    if not path.exists():
        path.write_text(body, encoding="utf-8")
    os.chmod(path, 0o600)
    return path


def load_packet(path: Path) -> dict[str, Any]:
    path = path.expanduser()
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o777 != 0o600:
        raise CandidatePlannerError("public_job_packet_not_private")
    packet = _object(path, "public_job_packet")
    body = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    if (
        packet.get("version") != 1 or packet.get("provider") != "upwork"
        or packet.get("kind") != "public_job"
        or hashlib.sha256(body.encode()).hexdigest() != path.stem
    ):
        raise CandidatePlannerError("public_job_packet_invalid")
    return packet


def planner_prompt(packet: dict[str, Any], owner_profile: dict[str, Any]) -> str:
    return """You are the autonomous acquisition judgment inside a 24/7 Upwork business loop.
Return only schema-valid JSON. Decide submit only when the official job is open, its exact scope is
fully deliverable with INSTALLED_SKILLS, the owner facts support every claim, the terms are profitable,
and all explicit screening questions can be answered truthfully. Otherwise skip with concise reasons.
Do not use keyword matching. Read the complete evidence and reason about scope, acceptance criteria,
client risk, competition, time, price, Connects, proof, and delivery capacity. Never invent experience,
identity, credentials, availability, results, client facts, requirements, portfolio, or attachments.
For submit, copy job_id, job_url, title, job_source_sha256, required_connects and
available_connects_before exactly from OFFICIAL_JOB. Set status=frozen_waiting_for_connects,
unsupported_claims=[], attachments=[]. Make the proposal specific and concise; ask a scope question
when needed but do not promise unsupported work or provide the finished solution for free.
OWNER_PROFILE=""" + json.dumps(owner_profile, ensure_ascii=False, sort_keys=True) + \
        "\nOFFICIAL_JOB=" + json.dumps(packet, ensure_ascii=False, sort_keys=True)


def validate_decision(decision: dict[str, Any], packet: dict[str, Any]) -> dict[str, Any] | None:
    if set(decision) != {"decision", "reason_codes", "proposal"}:
        raise CandidatePlannerError("public_job_decision_invalid")
    reasons = decision.get("reason_codes")
    if not isinstance(reasons, list) or any(not isinstance(x, str) or not x for x in reasons):
        raise CandidatePlannerError("public_job_decision_invalid")
    if decision.get("decision") == "skip":
        if decision.get("proposal") is not None or not reasons:
            raise CandidatePlannerError("public_job_decision_invalid")
        return None
    proposal = decision.get("proposal")
    terms = proposal.get("terms") if isinstance(proposal, dict) else None
    answers = proposal.get("screening_answers") if isinstance(proposal, dict) else None
    expected = {
        "provider", "job_id", "job_url", "job_source_sha256", "title", "status",
        "terms", "cover_letter", "screening_answers", "unsupported_claims", "attachments",
    }
    if (
        decision.get("decision") != "submit" or not isinstance(proposal, dict)
        or set(proposal) != expected or proposal.get("provider") != "upwork"
        or proposal.get("job_id") != packet.get("job_id")
        or proposal.get("job_url") != packet.get("job_url")
        or proposal.get("title") != packet.get("title")
        or proposal.get("job_source_sha256") != packet.get("detail_evidence_sha256")
        or proposal.get("status") != "frozen_waiting_for_connects"
        or not isinstance(proposal.get("cover_letter"), str)
        or len(proposal["cover_letter"].strip()) < 80
        or not isinstance(terms, dict) or set(terms) != {
            "type", "bid_usd", "delivery_days", "required_connects", "available_connects_before",
        }
        or terms.get("type") not in {"fixed_price", "hourly"}
        or not isinstance(terms.get("bid_usd"), (int, float))
        or isinstance(terms.get("bid_usd"), bool) or terms["bid_usd"] <= 0
        or type(terms.get("delivery_days")) is not int or not 1 <= terms["delivery_days"] <= 365
        or terms.get("required_connects") != packet.get("connects_required")
        or terms.get("available_connects_before") != packet.get("available_connects_before")
        or not isinstance(answers, list)
        or any(not isinstance(a, dict) or set(a) != {"question", "answer"}
               or not all(isinstance(a[k], str) and a[k].strip() for k in a) for a in answers)
        or proposal.get("unsupported_claims") != [] or proposal.get("attachments") != []
    ):
        raise CandidatePlannerError("public_job_decision_mismatch")
    body = json.dumps(proposal, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    return {**proposal, "payload_sha256": hashlib.sha256(body.encode()).hexdigest()}


def invoke(
    packet_path: Path, *, evidence_dir: Path, runner: Path = DEFAULT_RUNNER,
    schema: Path = DEFAULT_SCHEMA, profile: Path = DEFAULT_PROFILE,
) -> tuple[dict[str, Any] | None, list[str]]:
    packet = load_packet(packet_path)
    evidence_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(evidence_dir, 0o700)
    summary = evidence_dir / "summary.json"
    if not summary.is_file():
        completed = subprocess.run([
            sys.executable, str(runner), "--task-class", "application-intent-planner",
            "--prompt-stdin", "--schema", str(schema), "--evidence-dir", str(evidence_dir),
            "--task-label", "upwork-public-proposal", "--loop", "gig-upwork",
            "--workdir", str(Path.home()), "--timeout-seconds", "420",
            "--escalation-reason", "client-facing public Upwork qualification and proposal",
        ], input=planner_prompt(packet, _object(profile.expanduser(), "owner_profile")),
            text=True, capture_output=True, timeout=450, check=False)
        if completed.returncode != 0:
            raise CandidatePlannerError("public_job_planner_failed")
    result_summary = _object(summary, "planner_summary")
    if result_summary.get("status") != "success":
        raise CandidatePlannerError("public_job_planner_failed")
    try:
        result = Path(str(result_summary["result_path"])).resolve()
        result.relative_to(evidence_dir.resolve())
    except (KeyError, OSError, ValueError) as exc:
        raise CandidatePlannerError("public_job_planner_result_unowned") from exc
    proposal = validate_decision(_object(result, "planner_result"), packet)
    for path in evidence_dir.rglob("*"):
        if path.is_file() and not path.is_symlink():
            os.chmod(path, 0o600)
    return proposal, list(_object(result, "planner_result")["reason_codes"])


def write_sealed_proposal(proposal: dict[str, Any], root: Path) -> Path:
    job_id, digest = proposal.get("job_id"), proposal.get("payload_sha256")
    if not isinstance(job_id, str) or not re.fullmatch(r"~\d{15,}", job_id) \
            or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise CandidatePlannerError("sealed_public_proposal_invalid")
    root = root.expanduser()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    path = root / f"{job_id.lstrip('~')}.json"
    body = json.dumps(proposal, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != body:
        raise CandidatePlannerError("sealed_public_proposal_immutable")
    if not path.exists():
        path.write_text(body, encoding="utf-8")
    os.chmod(path, 0o600)
    return path
