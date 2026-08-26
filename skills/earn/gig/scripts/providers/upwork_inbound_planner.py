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
from typing import Any, Callable
from urllib.parse import urlsplit


HERE = Path(__file__).resolve()
GIG_ROOT = HERE.parents[2]
REPO_ROOT = HERE.parents[5]
SCRIPTS = GIG_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from application_planner import common_marketplace_feasibility_policy  # noqa: E402

DEFAULT_RUNNER = GIG_ROOT / "agent-runner/agent_runner.py"
DEFAULT_SCHEMA = GIG_ROOT / "schemas/upwork_inbound_proposal.schema.json"
DEFAULT_PROFILE = Path.home() / ".config/anicca/job-search/profile.json"
DEFAULT_MARKET_PROFILE = Path.home() / ".config/anicca/gig/upwork-profile-state.json"


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


def _optional_object(path: Path, label: str) -> dict[str, Any]:
    return _object(path, label) if path.is_file() else {}


def _market_proof(path: Path) -> dict[str, Any]:
    value = _optional_object(path, "market_profile")
    projects = value.get("portfolio_projects", [])
    if not isinstance(projects, list):
        raise InboundPlannerError("market_profile_invalid")
    return {
        "provider": value.get("provider"),
        "profile_id": value.get("profile_id"),
        "portfolio_projects": [
            {key: project.get(key) for key in (
                "project_id", "title", "public_profile_path", "source_url",
                "official_profile_readback",
            )}
            for project in projects if isinstance(project, dict)
        ],
    }


def load_packet(path: Path) -> dict[str, Any]:
    path = path.expanduser()
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o777 != 0o600:
        raise InboundPlannerError("inbound_packet_not_private")
    packet = _object(path, "inbound_packet")
    expected = {
        "version", "provider", "kind", "resource_id", "resource_url",
        "detail_evidence_sha256", "observed_at", "rendered_text", "title",
    }
    kind = packet.get("kind")
    if kind == "public_job":
        expected |= {"required_connects", "available_connects_before"}
    canonical = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    if (
        set(packet) != expected or packet.get("version") != 1 or packet.get("provider") != "upwork"
        or kind not in {"invitation_detected", "public_job"}
        or not isinstance(packet.get("resource_id"), str)
        or not isinstance(packet.get("title"), str) or not packet["title"].strip()
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
    packet: dict[str, Any], owner_profile: dict[str, Any],
) -> str:
    facts = json.dumps(owner_profile, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    inbound = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    common_policy = common_marketplace_feasibility_policy()
    required = packet.get("required_connects", 0)
    available = packet.get("available_connects_before", 0)
    status = "frozen_waiting_for_connects" if packet.get("kind") == "public_job" else "frozen_waiting_for_invitation"
    return f"""You decide one Upwork proposal. Return only schema-valid JSON with a decisions array
containing exactly one item. Copy resource_id into both decision.job_id and proposal.job_id.
{common_policy}
Use only facts present in OWNER_PROFILE and OFFICIAL_INBOUND. Never invent experience, identity,
availability, credentials, portfolio, results, client facts, requirements, questions, or scope.
Although the legacy field is named reason_codes, write one to three concise natural Japanese
sentences that an owner can understand. Never return enum names, snake_case slugs or keyword codes.
Choose skip only under the common policy. Missing pre-contract implementation details become concise
client questions rather than automatic rejection.
The market profile contains provider-published portfolio proof; use only its exact facts and public IDs.
Bid and delivery estimate are seller decisions: choose them within the official displayed budget/rate
when one exists. When the client displays no range, choose a reasonable seller rate from scope,
general agent delivery capacity, delivery effort and positive expected value; state the assumption.
For submit, copy job_id, job_url and job_source_sha256 exactly; status is {status}, required_connects
is {required}, available_connects_before is {available}; unsupported_claims and attachments are empty. Keep all
pre-contract communication on Upwork. The proposal must be specific, concise, truthful, and answer
every explicit screening question exactly once.
OWNER_PROFILE={facts}
OFFICIAL_INBOUND={inbound}"""


def batch_planner_prompt(
    packets: list[dict[str, Any]], owner_profile: dict[str, Any],
) -> str:
    facts = json.dumps(owner_profile, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    inbound = json.dumps(packets, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    common_policy = common_marketplace_feasibility_policy()
    return f"""Return one schema-valid decision for every item in OFFICIAL_CANDIDATES, in the same
order, with no omission. Copy each resource_id into decision.job_id and proposal.job_id.
{common_policy}
Return submit for every candidate the general agent can truthfully complete and whose official Connects
cost is covered. Do not use missing rate, unverified payment, new-client history, competition, duration
or Connects cost alone as skip; price and ask questions instead. Return skip only under the common policy
or when displayed compensation makes every truthful scoped offer clearly negative; include that candidate's own
natural-language reasons. Never limit the batch to one winner. Compare candidates, but do not suppress
one profitable candidate because another is better. Use only supplied facts. Never invent experience, identity,
availability, credentials, portfolio, results, client facts, requirements, questions or scope.
Although the legacy field is named reason_codes, write one to three concise natural Japanese
sentences that explain the actual comparison. Never return enum names, snake_case slugs or keyword codes.
Missing implementation details may become concise pre-contract questions. The market profile contains provider-published
portfolio proof; use only its exact facts and public IDs. Bid and delivery estimate are seller
decisions: choose them within the official displayed budget/rate and general agent capacity, with
positive expected value and an explicit assumption when needed. When no client range is displayed,
choose a reasonable seller rate from scope, delivery capacity and effort rather than treating
the missing client value as a blocker. For submit, copy the chosen resource_id, URL,
detail hash, required_connects and available_connects_before exactly; status is
frozen_waiting_for_connects; unsupported_claims and attachments are empty; answer every explicit
screening question exactly once and keep communication on Upwork.
OWNER_PROFILE={facts}
OFFICIAL_CANDIDATES={inbound}"""


def validate_decision(
    decision: dict[str, Any], packet: dict[str, Any],
) -> dict[str, Any] | None:
    if set(decision) != {"job_id", "decision", "reason_codes", "proposal"}:
        raise InboundPlannerError("inbound_decision_invalid")
    if decision.get("job_id") != packet["resource_id"]:
        raise InboundPlannerError("inbound_decision_mismatch")
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


def application_decision_event(
    decision: dict[str, Any], packet: dict[str, Any], *, title: str, occurred_at: str,
) -> dict[str, Any]:
    """Project one validated Luna decision into the shared Gig WorkEvent shape."""
    proposal = validate_decision(decision, packet)
    clean_title = title.strip() if isinstance(title, str) else ""
    if not clean_title or not isinstance(occurred_at, str) or not occurred_at.strip():
        raise InboundPlannerError("application_decision_event_invalid")
    canonical = json.dumps(decision, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    decision_sha256 = hashlib.sha256(canonical.encode()).hexdigest()
    submitted = proposal is not None
    reasons = list(decision["reason_codes"])
    return {
        "event_key": (
            f"gig:application-decision:upwork:{packet['resource_id']}:"
            f"{packet['detail_evidence_sha256']}:{decision_sha256}"
        ),
        "kind": "application",
        "entity_id": packet["resource_id"],
        "occurred_at": occurred_at,
        "state": "selected" if submitted else "skipped",
        "action": "応募準備" if submitted else "応募見送り",
        "result": "Lunaが応募対象に選定しました" if submitted else "Lunaが応募しないと判断しました",
        "next_action": "公式preflight後に応募します" if submitted else "次の案件確認を続けます",
        "evidence": ["official_job", "model_decision"],
        "attributes": {
            "platform": "upwork",
            "title": clean_title,
            "url": packet["resource_url"],
            "decision": decision["decision"],
            "reason_codes": reasons,
            "decision_sha256": decision_sha256,
            "job_source_sha256": packet["detail_evidence_sha256"],
            "terms": proposal["terms"] if submitted else None,
            "quote": ({
                "currency": "USD", "amount": proposal["terms"]["bid_usd"],
                "unit": proposal["terms"]["type"],
            } if submitted else None),
        },
    }


def _invoke_prompt(
    prompt: str, *, runner: Path, schema: Path, evidence_dir: Path,
) -> dict[str, Any]:
    prompt_sha = hashlib.sha256(prompt.encode()).hexdigest()
    binding = evidence_dir / "prompt.sha256"
    if evidence_dir.joinpath("summary.json").is_file() and (
        not binding.is_file() or binding.read_text(encoding="utf-8").strip() != prompt_sha
    ):
        evidence_dir = evidence_dir / f"prompt-{prompt_sha}"
        binding = evidence_dir / "prompt.sha256"
    evidence_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(evidence_dir, 0o700)
    if not binding.is_file():
        binding.write_text(prompt_sha + "\n", encoding="utf-8")
        os.chmod(binding, 0o600)
    summary_path = evidence_dir / "summary.json"
    if not summary_path.is_file():
        completed = subprocess.run([
            sys.executable, str(runner), "--task-class", "application-intent-planner",
            "--prompt-stdin", "--schema", str(schema), "--evidence-dir", str(evidence_dir),
            "--task-label", "upwork-inbound-proposal", "--loop", "gig-upwork",
            "--workdir", str(Path.home()), "--timeout-seconds", "420",
            "--escalation-reason", "client-facing Upwork application decision",
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
    decision = _object(result, "planner_result")
    for path in evidence_dir.rglob("*"):
        if path.is_file() and not path.is_symlink():
            os.chmod(path, 0o600)
    return decision


def validate_batch_result(
    result: dict[str, Any], packets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    decisions = result.get("decisions") if isinstance(result, dict) and set(result) == {"decisions"} else None
    expected_ids = [packet["resource_id"] for packet in packets]
    if (
        not isinstance(decisions, list) or len(decisions) != len(packets)
        or [decision.get("job_id") if isinstance(decision, dict) else None for decision in decisions]
        != expected_ids
    ):
        raise InboundPlannerError("inbound_batch_result_invalid")
    return decisions


def invoke(
    packet_path: Path, *, runner: Path = DEFAULT_RUNNER, schema: Path = DEFAULT_SCHEMA,
    profile: Path = DEFAULT_PROFILE, market_profile: Path = DEFAULT_MARKET_PROFILE,
    evidence_dir: Path, decision_sink: Callable[[list[dict[str, Any]]], None] | None = None,
    title: str = "",
) -> dict[str, Any] | None:
    packet = load_packet(packet_path)
    facts = {
        "owner": _object(profile.expanduser(), "owner_profile"),
        "market": _market_proof(market_profile.expanduser()),
    }
    prompt = planner_prompt(
        packet, facts,
    )
    result = _invoke_prompt(prompt, runner=runner, schema=schema, evidence_dir=evidence_dir)
    decisions = validate_batch_result(result, [packet])
    decision = decisions[0]
    proposal = validate_decision(decision, packet)
    if decision_sink is not None:
        decision_sink([application_decision_event(
            decision, packet, title=(proposal or {}).get("title") or title or packet["resource_id"],
            occurred_at=packet["observed_at"],
        )])
    return proposal


def invoke_batch(
    packet_paths: list[Path], *, runner: Path = DEFAULT_RUNNER, schema: Path = DEFAULT_SCHEMA,
    profile: Path = DEFAULT_PROFILE, market_profile: Path = DEFAULT_MARKET_PROFILE,
    evidence_dir: Path, decision_sink: Callable[[list[dict[str, Any]]], None] | None = None,
) -> list[dict[str, Any]]:
    packets = [load_packet(path) for path in packet_paths]
    if not packets or len(packets) > 10 or any(packet.get("kind") != "public_job" for packet in packets):
        raise InboundPlannerError("inbound_batch_invalid")
    facts = {
        "owner": _object(profile.expanduser(), "owner_profile"),
        "market": _market_proof(market_profile.expanduser()),
    }
    prompt = batch_planner_prompt(
        packets, facts,
    )
    result = _invoke_prompt(prompt, runner=runner, schema=schema, evidence_dir=evidence_dir)
    decisions = validate_batch_result(result, packets)
    proposals = []
    events = []
    for packet, decision in zip(packets, decisions, strict=True):
        proposal = validate_decision(decision, packet)
        events.append(application_decision_event(
            decision, packet, title=(proposal or {}).get("title") or packet["title"],
            occurred_at=packet["observed_at"],
        ))
        if proposal is not None:
            proposals.append(proposal)
    if decision_sink is not None:
        decision_sink(events)
    return proposals


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
