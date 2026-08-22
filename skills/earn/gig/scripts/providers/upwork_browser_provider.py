#!/usr/bin/env python3
"""Read authenticated Upwork zero-spend state through the existing CloakBrowser CDP helper."""

from __future__ import annotations

import argparse
import asyncio
import fcntl
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from cdp_nav_snapshot import navigate_and_snapshot  # noqa: E402
from connector_outbox import ConnectorOutbox  # noqa: E402
from provider_authorization import DEFAULT_RECEIPT_PATH  # noqa: E402
from upwork_proposal_browser import submit_proposal_after_fence  # noqa: E402
from upwork_inbound_planner import invoke as plan_inbound, write_sealed_proposal  # noqa: E402
from upwork_offer_gate import invoke as qualify_direct_offer  # noqa: E402
from upwork_offer_browser import accept_offer_after_fence  # noqa: E402
from upwork_offer_effect import SealedUpworkOfferEffect  # noqa: E402
from upwork_inbox import append_changed_heads, normalize_observation  # noqa: E402
from upwork_negotiate import invoke as plan_negotiation  # noqa: E402
from upwork_sealed_effect import (  # noqa: E402
    SealedUpworkProposalEffect, active_upwork_browser_account,
)
from upwork_transport import UpworkTransport  # noqa: E402


CONNECTS_URL = "https://www.upwork.com/nx/plans/connects/history"
INVITES_URL = "https://www.upwork.com/nx/find-work/invites"
PROPOSALS_URL = "https://www.upwork.com/nx/proposals/"
CATALOG_URL = "https://www.upwork.com/nx/project-dashboard/?step=approved"
CONTRACTS_URL = "https://www.upwork.com/nx/wm/freelancer/home"
MESSAGES_URL = "https://www.upwork.com/ab/messages/rooms/"
WORKING_STYLE_URL = "https://www.upwork.com/nx/skills-assesment/assessment-results"
DEFAULT_CANDIDATES = SCRIPTS.parent / "config" / "upwork-candidates.public.json"
DEFAULT_TRANSITIONS = Path.home() / "gig/state/upwork-free-transitions.jsonl"
DEFAULT_PROPOSALS = Path.home() / ".config/anicca/gig/upwork-proposals"
DEFAULT_DATABASE = Path.home() / "gig/connector-outbox.sqlite3"
DEFAULT_MANIFEST = SCRIPTS.parent / "config/connectors/coconala.json"
DEFAULT_BROWSER_PROFILE = Path.home() / ".cloak/profiles/gig-daily-driver"
DEFAULT_INBOUND_DIR = Path.home() / ".config/anicca/gig/upwork-inbound"
DEFAULT_INBOUND_PROPOSALS = Path.home() / ".config/anicca/gig/upwork-inbound-proposals"
DEFAULT_INBOUND_EVIDENCE = Path.home() / "gig/state/upwork-inbound-planner"
DEFAULT_OFFER_EVIDENCE = Path.home() / "gig/state/upwork-offer-gate"
DEFAULT_INBOX_LEDGER = Path.home() / "gig/state/upwork-inbox.jsonl"
DEFAULT_NEGOTIATION_EVIDENCE = Path.home() / "gig/state/upwork-negotiation-planner"
TERMINAL_JOB_STATUSES = {"closed", "removed"}
_COUNT_LABELS = {
    "offers": r"Offers\s*\((\d+)\)",
    "invites": r"Invites from clients\s*\((\d+)\)",
    "active_proposals": r"Active proposals\s*\((\d+)\)",
    "submitted_proposals": r"Submitted proposals\s*\((\d+)\)",
}
_CONNECTS_REQUIRED = re.compile(
    r"Send a proposal for:\s*(\d+)\s+Connects|"
    r"Required Connects to submit a proposal:\s*(\d+)",
    re.IGNORECASE,
)


def parse_connects(text: str) -> dict[str, Any]:
    match = re.search(r"My balance\s+(\d+)\s+Connects\b", text or "", re.IGNORECASE)
    if match is None:
        raise ValueError("upwork_readback_incomplete")
    return {
        "balance": int(match.group(1)),
        "transactions_empty": "No Connects transactions." in text,
    }


def parse_inventory(text: str, working_style_text: str = "") -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field, pattern in _COUNT_LABELS.items():
        match = re.search(pattern, text or "", re.IGNORECASE)
        if match is None:
            raise ValueError("upwork_readback_incomplete")
        result[field] = int(match.group(1))
    strengths = [
        label for label in ("Accountable for outcomes", "Detail-oriented")
        if label.casefold() in working_style_text.casefold()
    ]
    working_style_complete = (
        "working style assessment results" in working_style_text.casefold()
        and working_style_text.casefold().count("shown on profile") >= 2
        and len(strengths) == 2
    )
    tasks: list[str] = []
    if (
        re.search(r"Take the working style assessment", text, re.IGNORECASE)
        and not working_style_complete
    ):
        tasks.append("working_style_assessment")
    result["account_tasks"] = tasks
    result["working_style"] = {
        "completed": working_style_complete,
        "strengths": strengths,
    }
    return result


def parse_catalog(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field, label in (
        ("catalog_approved", "Approved"),
        ("catalog_under_review", "Under Review"),
        ("catalog_drafts", "Drafts"),
    ):
        match = re.search(rf"{label}\s*\((\d+)\)", text or "", re.IGNORECASE)
        if match is None:
            raise ValueError("upwork_readback_incomplete")
        result[field] = int(match.group(1))
    projects = []
    for match in re.finditer(
        r"Visible\s+([^\n]+)\s+(\d+)\s+(\d+)\s+More Project Options",
        text or "", re.IGNORECASE,
    ):
        projects.append({
            "title": match.group(1).strip(),
            "visible": True,
            "views_30d": int(match.group(2)),
            "orders": int(match.group(3)),
        })
    if result["catalog_approved"] and not projects:
        raise ValueError("upwork_readback_incomplete")
    result["catalog_projects"] = projects
    return result


def _stable_link(link: dict[str, Any]) -> dict[str, str] | None:
    href = str(link.get("href") or "")
    match = re.search(r"/jobs/[^/?#]*(~[A-Za-z0-9]+)(?:[/?#]|$)", href)
    if match is None:
        match = re.search(
            r"/(?:proposals|workroom|rooms)/([^/?#]+)(?:[/?#]|$)", href,
        )
    if match is None or match.group(1).lower() in {"archived", "referrals"}:
        return None
    return {
        "id": match.group(1),
        "href": href.split("?", 1)[0],
        "title": str(link.get("text") or "").strip(),
    }


def _dedupe_links(links: list[dict[str, Any]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for link in links:
        entity = _stable_link(link)
        if entity is None:
            continue
        key = (entity["id"], entity["href"])
        if key not in seen:
            seen.add(key)
            result.append(entity)
    return result


def parse_stable_entities(
    *, invite_links: list[dict[str, Any]], proposal_links: list[dict[str, Any]],
) -> dict[str, Any]:
    invitations = _dedupe_links(invite_links)
    offers: list[dict[str, str]] = []
    active: list[dict[str, str]] = []
    submitted: list[dict[str, str]] = []
    unknown: list[dict[str, str]] = []
    for link in proposal_links:
        entity = _stable_link(link)
        if entity is None:
            continue
        context = " ".join(str(link.get(key) or "") for key in (
            "context", "text", "aria", "data_qa", "class_name",
        )).lower()
        if "offer" in context:
            target = offers
        elif "submitted" in context:
            target = submitted
        elif "active" in context:
            target = active
        else:
            target = unknown
        if entity not in target:
            target.append(entity)
    return {
        "invitation_entities": invitations,
        "proposal_offer_entities": offers,
        "active_proposal_entities": active,
        "submitted_proposal_entities": submitted,
        "unclassified_proposal_entities": unknown,
    }


def parse_contracts(text: str, links: list[dict[str, Any]]) -> dict[str, Any]:
    match = re.search(r"Earnings available now:\s*\$([\d,]+\.\d{2})", text or "")
    if match is None:
        raise ValueError("upwork_readback_incomplete")
    contracts = [
        item for item in _dedupe_links(links)
        if "/workroom/" in item["href"] or "contract" in item["href"].lower()
    ]
    if "There are no active contracts." not in text and not contracts:
        raise ValueError("upwork_readback_incomplete")
    return {
        "earnings_available_usd_minor": int(
            Decimal(match.group(1).replace(",", "")) * 100
        ),
        "active_contracts": contracts,
    }


def parse_messages(text: str, links: list[dict[str, Any]]) -> dict[str, Any]:
    rooms = [
        item for item in _dedupe_links(links)
        if "/ab/messages/rooms/" in item["href"]
    ]
    if "Conversations will appear here" not in text and not rooms:
        raise ValueError("upwork_readback_incomplete")
    unread = []
    for link in links:
        entity = _stable_link(link)
        marker = " ".join(str(link.get(key) or "") for key in (
            "context", "aria", "data_qa", "class_name",
        )).lower()
        if entity and "/ab/messages/rooms/" in entity["href"] and "unread" in marker:
            unread.append(entity["id"])
    return {"message_rooms": rooms, "unread_message_room_ids": sorted(set(unread))}


def load_candidates(path: Path) -> list[dict[str, str]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    candidates = value.get("candidates") if isinstance(value, dict) else None
    if not isinstance(candidates, list):
        raise ValueError("upwork_candidate_config_invalid")
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in candidates:
        if not isinstance(item, dict):
            raise ValueError("upwork_candidate_config_invalid")
        job_id = str(item.get("job_id") or "")
        job_url = str(item.get("job_url") or "")
        if not re.fullmatch(r"~\d{15,}", job_id) or job_id not in job_url or job_id in seen:
            raise ValueError("upwork_candidate_config_invalid")
        seen.add(job_id)
        candidate = {key: str(item.get(key) or "") for key in (
            "job_id", "job_url", "queue", "title", "proposal_payload_sha256",
        )}
        if candidate["queue"] == "ready" and not re.fullmatch(
            r"[0-9a-f]{64}", candidate["proposal_payload_sha256"],
        ):
            raise ValueError("upwork_candidate_config_invalid")
        result.append(candidate)
    return result


_SEALED_PROPOSAL_KEYS = {
    "attachments", "cover_letter", "job_id", "job_source_sha256", "job_url",
    "payload_sha256", "provider", "screening_answers", "status", "terms",
    "title", "unsupported_claims",
}
_SEALED_TERMS_KEYS = {
    "type", "bid_usd", "delivery_days", "required_connects",
    "available_connects_before",
}


def plan_free_proposal(state: dict[str, Any], proposals_dir: Path) -> dict[str, Any] | None:
    """Return the first exact sealed proposal covered by the observed free balance."""
    balance = state.get("balance")
    candidates = state.get("candidate_jobs")
    if type(balance) is not int or balance < 0 or not isinstance(candidates, list):
        raise ValueError("upwork_free_action_state_invalid")
    if balance == 0:
        return None
    proposals_dir = proposals_dir.expanduser()
    if (
        proposals_dir.is_symlink() or not proposals_dir.is_dir()
        or proposals_dir.stat().st_mode & 0o777 != 0o700
    ):
        raise ValueError("upwork_proposal_store_invalid")
    for candidate in candidates:
        if (
            not isinstance(candidate, dict) or candidate.get("status") != "open"
            or candidate.get("queue") != "ready"
        ):
            continue
        required = candidate.get("connects_required")
        if type(required) is not int or required < 0 or balance < required:
            continue
        job_id = candidate.get("job_id")
        expected_hash = candidate.get("proposal_payload_sha256")
        if (
            not isinstance(job_id, str) or not job_id.startswith("~")
            or not isinstance(expected_hash, str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected_hash)
        ):
            raise ValueError("upwork_free_action_candidate_invalid")
        path = proposals_dir / f"{job_id.lstrip('~')}.json"
        if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o777 != 0o600:
            raise ValueError("upwork_sealed_proposal_invalid")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("upwork_sealed_proposal_invalid") from exc
        if not isinstance(payload, dict) or set(payload) != _SEALED_PROPOSAL_KEYS:
            raise ValueError("upwork_sealed_proposal_invalid")
        terms = payload.get("terms")
        answers = payload.get("screening_answers")
        proposal_url = urlsplit(str(payload.get("job_url") or ""))
        if (
            payload.get("provider") != "upwork" or payload.get("job_id") != job_id
            or proposal_url.scheme != "https" or proposal_url.netloc != "www.upwork.com"
            or job_id not in proposal_url.path
            or payload.get("status") != "frozen_waiting_for_connects"
            or not re.fullmatch(r"[0-9a-f]{64}", str(payload.get("job_source_sha256") or ""))
            or not isinstance(payload.get("cover_letter"), str)
            or not payload["cover_letter"].strip()
            or not isinstance(terms, dict) or set(terms) != _SEALED_TERMS_KEYS
            or terms.get("required_connects") != required
            or not isinstance(answers, list)
            or any(
                not isinstance(answer, dict) or set(answer) != {"question", "answer"}
                or not all(isinstance(answer[key], str) and answer[key].strip() for key in answer)
                for answer in answers
            )
            or payload.get("unsupported_claims") != []
            or not isinstance(payload.get("attachments"), list)
        ):
            raise ValueError("upwork_sealed_proposal_invalid")
        canonical = dict(payload)
        recorded_hash = canonical.pop("payload_sha256")
        canonical_line = json.dumps(
            canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ) + "\n"
        actual_hash = hashlib.sha256(canonical_line.encode()).hexdigest()
        if recorded_hash != expected_hash or actual_hash != expected_hash:
            raise ValueError("upwork_sealed_proposal_hash_mismatch")
        return payload
    return None


def plan_zero_connect_inbound(state: dict[str, Any]) -> dict[str, Any] | None:
    """Prioritize one stable-ID inbound acquisition that needs no Connects."""
    for field, kind in (
        ("proposal_offer_entities", "direct_offer_detected"),
        ("invitation_entities", "invitation_detected"),
    ):
        entities = state.get(field)
        if not isinstance(entities, list):
            raise ValueError("upwork_free_action_state_invalid")
        if entities:
            entity = entities[0]
            resource_url = urlsplit(str(entity.get("href") or "")) if isinstance(entity, dict) else None
            if (
                not isinstance(entity, dict) or not isinstance(entity.get("id"), str)
                or not isinstance(entity.get("href"), str)
                or resource_url is None or resource_url.scheme != "https"
                or resource_url.netloc != "www.upwork.com"
                or entity["id"] not in entity["href"]
            ):
                raise ValueError("upwork_free_action_state_invalid")
            return {
                "state": kind, "resource_id": entity["id"],
                "resource_url": entity["href"],
            }
    projects = state.get("catalog_projects")
    if not isinstance(projects, list):
        raise ValueError("upwork_free_action_state_invalid")
    ordered = next((item for item in projects if isinstance(item, dict) and item.get("orders", 0) > 0), None)
    if ordered is not None:
        return {"state": "catalog_order_identity_pending", "order_count": ordered["orders"]}
    return None


def parse_zero_connect_detail(kind: str, text: str) -> str:
    """Classify only official controls; never infer that an inbound is actionable."""
    normalized = " ".join((text or "").lower().split())
    if kind == "invitation_detected":
        accept = any(marker in normalized for marker in (
            "accept and send a proposal", "submit a proposal", "accept interview",
        ))
    elif kind == "direct_offer_detected":
        accept = "accept offer" in normalized
    else:
        raise ValueError("upwork_inbound_kind_invalid")
    return "actionable" if accept and "decline" in normalized else "unknown"


def seal_inbound_detail(
    inbound: dict[str, Any], text: str, evidence_sha256: str, root: Path,
    observed_at: str,
) -> str:
    """Persist one actionable inbound privately for the existing model runner."""
    if (
        inbound.get("state") not in {"invitation_detected", "direct_offer_detected"}
        or not isinstance(inbound.get("resource_id"), str)
        or not isinstance(inbound.get("resource_url"), str)
        or not isinstance(text, str) or not text.strip()
        or not re.fullmatch(r"[0-9a-f]{64}", evidence_sha256)
    ):
        raise ValueError("upwork_inbound_packet_invalid")
    root = root.expanduser()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    packet = {
        "version": 1, "provider": "upwork", "kind": inbound["state"],
        "resource_id": inbound["resource_id"], "resource_url": inbound["resource_url"],
        "detail_evidence_sha256": evidence_sha256, "observed_at": observed_at,
        "rendered_text": text,
    }
    body = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    digest = hashlib.sha256(body.encode()).hexdigest()
    path = root / f"{digest}.json"
    if not path.exists():
        _atomic_write(path, packet)
    if path.is_symlink() or path.stat().st_mode & 0o777 != 0o600:
        raise ValueError("upwork_inbound_packet_invalid")
    return digest


def parse_candidate(
    candidate: dict[str, str], text: str, evidence_sha256: str,
) -> dict[str, Any]:
    lowered = (text or "").lower()
    if "this job has been removed" in lowered or "removed from upwork" in lowered:
        status, marker = "removed", "removed"
    elif "this job is no longer available" in lowered:
        status, marker = "closed", "no_longer_available"
    elif _CONNECTS_REQUIRED.search(text or "") and "Available Connects:" in (text or ""):
        status, marker = "open", "proposal_entry"
    else:
        status, marker = "unknown", "no_authoritative_marker"
    connects = _CONNECTS_REQUIRED.search(text or "")
    return {
        **candidate,
        "status": status,
        "official_marker": marker,
        "connects_required": int(next(value for value in connects.groups() if value))
        if connects else None,
        "evidence_sha256": evidence_sha256,
    }


def _read_evidence(path: Path, expected_url: str) -> tuple[str, str, list[dict[str, Any]]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("navigated_ok") is not True or value.get("url") != expected_url:
        raise ValueError("upwork_readback_incomplete")
    text = value.get("rendered_text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("upwork_readback_incomplete")
    links = value.get("rendered_links", [])
    if not isinstance(links, list):
        raise ValueError("upwork_readback_incomplete")
    return text, hashlib.sha256(path.read_bytes()).hexdigest(), links


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def _read_previous_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("upwork_previous_state_invalid") from error
    if not isinstance(value, dict):
        raise ValueError("upwork_previous_state_invalid")
    return value


def reconcile_terminal_transitions(
    output: Path, ledger: Path, state: dict[str, Any],
) -> dict[str, Any]:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a+", encoding="utf-8") as handle:
        os.chmod(ledger, 0o600)
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            previous = _read_previous_state(output)
            handle.seek(0)
            rows = []
            for line in handle:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as error:
                    raise ValueError("upwork_transition_ledger_invalid") from error
                if not isinstance(row, dict) or not row.get("event_id"):
                    raise ValueError("upwork_transition_ledger_invalid")
                rows.append(row)
            existing_ids = {str(row["event_id"]) for row in rows}
            existing_terminal = {
                (str(row.get("job_id")), str(row.get("to_status"))) for row in rows
            }
            previous_jobs = {
                str(item.get("job_id")): item
                for item in previous.get("candidate_jobs", [])
                if isinstance(item, dict) and item.get("job_id")
            }
            appended = []
            for candidate in state.get("candidate_jobs", []):
                if not isinstance(candidate, dict):
                    continue
                job_id = str(candidate.get("job_id") or "")
                to_status = str(candidate.get("status") or "")
                if not job_id or to_status not in TERMINAL_JOB_STATUSES:
                    continue
                prior = previous_jobs.get(job_id, {})
                prior_status = str(prior.get("status") or "unobserved")
                if prior_status == to_status and (job_id, to_status) in existing_terminal:
                    continue
                from_status = "legacy_observed" if prior_status == to_status else prior_status
                source_observed_at = str(previous.get("observed_at") or "unobserved")
                event_material = "|".join((
                    job_id, from_status, to_status, source_observed_at,
                ))
                event_id = hashlib.sha256(event_material.encode("utf-8")).hexdigest()
                if event_id in existing_ids:
                    continue
                event = {
                    "event_id": event_id,
                    "job_id": job_id,
                    "from_status": from_status,
                    "to_status": to_status,
                    "official_reason": str(candidate.get("official_marker") or "unknown"),
                    "observed_at": str(state.get("observed_at") or ""),
                    "source_observed_at": source_observed_at,
                    "receipt_hash": str(candidate.get("evidence_sha256") or ""),
                }
                handle.write(json.dumps(
                    event, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                ) + "\n")
                appended.append(event)
                existing_ids.add(event_id)
                existing_terminal.add((job_id, to_status))
            handle.flush()
            os.fsync(handle.fileno())
            state = dict(state)
            state["terminal_transition_count"] = len(rows) + len(appended)
            state["terminal_transitions_appended"] = len(appended)
            state["terminal_transition_event_ids"] = [
                event["event_id"] for event in appended
            ]
            _atomic_write(output, state)
            return state
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


async def execute_sealed_proposal(
    payload: dict[str, Any], *, pass_id: str, sequence: int, database: Path,
    manifest: Path, browser_profile: Path,
) -> tuple[dict[str, Any], dict[str, Any] | None, str | None]:
    """Run either public or invitation proposal through the same durable effect."""
    effect_now = datetime.now(timezone.utc)
    effect = SealedUpworkProposalEffect(
        ConnectorOutbox(database.expanduser(), manifest.expanduser()),
        UpworkTransport(
            active_upwork_browser_account(DEFAULT_RECEIPT_PATH, effect_now), effect_now,
            browser_profile=browser_profile.expanduser(),
            profiles_root=browser_profile.expanduser().parent,
        ),
    )
    _, planned = effect.intent(payload)
    existing = effect.store.provider_effect(planned)
    base = {"proposal_payload_sha256": payload["payload_sha256"]}
    if existing is not None and existing["reconciliation_state"] == "verified":
        return {**base, "state": "submitted", "proposal_id": existing["proposal_id"]}, None, None
    if existing is not None and existing["state"] == "reconcile_pending":
        return {**base, "state": "reconcile_unknown"}, None, None
    holder: dict[str, Any] = {}

    def start_effect(preflight: dict[str, Any]) -> bool:
        holder["intent"], started = effect.start(payload, preflight)
        return started

    receipt = await submit_proposal_after_fence(payload, start_effect)
    artifact = Path(await navigate_and_snapshot(
        pass_id, f"{sequence:02d}-1", "connects-post", CONNECTS_URL,
        "read_only", 2, 1440,
    ))
    post_text, post_hash, _ = _read_evidence(artifact, CONNECTS_URL)
    post_connects = parse_connects(post_text)
    effect.verify(
        holder["intent"], receipt, connects_post=post_connects["balance"],
        connects_evidence_sha256=post_hash,
    )
    return {
        **base, "state": "submitted", "proposal_id": receipt["proposal_id"],
    }, post_connects, post_hash


async def execute_direct_offer(
    decision: dict[str, Any], *, database: Path, manifest: Path, browser_profile: Path,
) -> dict[str, Any]:
    """Accept one qualified Direct Offer through the shared durable effect ledger."""
    effect_now = datetime.now(timezone.utc)
    effect = SealedUpworkOfferEffect(
        ConnectorOutbox(database.expanduser(), manifest.expanduser()),
        UpworkTransport(
            active_upwork_browser_account(DEFAULT_RECEIPT_PATH, effect_now, "accept_offer"),
            effect_now, browser_profile=browser_profile.expanduser(),
            profiles_root=browser_profile.expanduser().parent,
        ),
    )
    _, planned = effect.intent(decision)
    existing = effect.store.provider_effect(planned)
    base = {"offer_decision_sha256": decision["decision_sha256"]}
    if existing is not None and existing["reconciliation_state"] == "verified":
        return {**base, "state": "accepted", "contract_id": existing["proposal_id"]}
    if existing is not None and existing["state"] == "reconcile_pending":
        return {**base, "state": "reconcile_unknown"}
    holder: dict[str, Any] = {}

    def start_effect(preflight: dict[str, Any]) -> bool:
        holder["intent"], started = effect.start(decision, preflight)
        return started

    receipt = await accept_offer_after_fence(decision, start_effect)
    effect.verify(holder["intent"], receipt)
    return {**base, "state": "accepted", "contract_id": receipt["contract_id"]}


async def observe(
    candidates_path: Path = DEFAULT_CANDIDATES,
    proposals_dir: Path = DEFAULT_PROPOSALS,
    database: Path = DEFAULT_DATABASE,
    manifest: Path = DEFAULT_MANIFEST,
    browser_profile: Path = DEFAULT_BROWSER_PROFILE,
    inbound_dir: Path = DEFAULT_INBOUND_DIR,
    inbound_proposals: Path = DEFAULT_INBOUND_PROPOSALS,
    inbound_evidence: Path = DEFAULT_INBOUND_EVIDENCE,
    inbox_ledger: Path = DEFAULT_INBOX_LEDGER,
) -> dict[str, Any]:
    pass_id = f"upwork-free-{time.time_ns()}-{os.getpid()}"
    artifacts: dict[str, str] = {}
    pages: dict[str, str] = {}
    links: dict[str, list[dict[str, Any]]] = {}
    candidates = load_candidates(candidates_path)
    targets = [
        ("connects", CONNECTS_URL), ("invites", INVITES_URL),
        ("proposals", PROPOSALS_URL), ("catalog", CATALOG_URL),
        ("contracts", CONTRACTS_URL), ("messages", MESSAGES_URL),
        ("working-style", WORKING_STYLE_URL),
    ] + [
        (f"candidate-{item['job_id'].lstrip('~')}", item["job_url"])
        for item in candidates
    ]
    for sequence, (label, url) in enumerate(targets, start=1):
        for attempt in range(1, 4):
            artifact = Path(await navigate_and_snapshot(
                pass_id, f"{sequence:02d}-{attempt}", label, url, "read_only", 2,
                1440,
            ))
            try:
                pages[label], artifacts[label], links[label] = _read_evidence(artifact, url)
                break
            except ValueError:
                if attempt == 3:
                    raise
                await asyncio.sleep(attempt)
    message_inventory = parse_messages(pages["messages"], links["messages"])
    inbox_observations: list[dict[str, Any]] = []
    for offset, room in enumerate(message_inventory["message_rooms"][:20], start=1):
        label = f"room-{hashlib.sha256(room['id'].encode()).hexdigest()[:16]}"
        artifact = Path(await navigate_and_snapshot(
            pass_id, f"{len(targets) + offset:02d}-1", label, room["href"],
            "read_only", 2, 1440,
        ))
        room_text, room_hash, room_links = _read_evidence(artifact, room["href"])
        pages[label], artifacts[label] = room_text, room_hash
        inbox_observations.append(normalize_observation(
            kind="message_room", resource_id=room["id"], resource_url=room["href"],
            rendered_text=room_text, source_evidence_sha256=room_hash,
            observed_at=datetime.now(timezone.utc).isoformat(),
            rendered_links=room_links,
        ))
    contract_inventory = parse_contracts(pages["contracts"], links["contracts"])
    for contract in contract_inventory["active_contracts"]:
        inbox_observations.append(normalize_observation(
            kind="contract", resource_id=contract["id"], resource_url=contract["href"],
            rendered_text=pages["contracts"], source_evidence_sha256=artifacts["contracts"],
            observed_at=datetime.now(timezone.utc).isoformat(),
        ))
    inbox_reconciliation = append_changed_heads(inbox_ledger, inbox_observations)
    state = {
        "version": 1,
        "provider": "upwork",
        "mode": "zero_spend",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        **parse_connects(pages["connects"]),
        **parse_inventory(
            pages["proposals"] + "\n" + pages["invites"],
            pages["working-style"],
        ),
        **parse_stable_entities(
            invite_links=links["invites"], proposal_links=links["proposals"],
        ),
        **parse_catalog(pages["catalog"]),
        **contract_inventory,
        **message_inventory,
        "inbox_reconciliation": inbox_reconciliation,
        "candidate_jobs": [
            parse_candidate(
                item,
                pages[f"candidate-{item['job_id'].lstrip('~') }"],
                artifacts[f"candidate-{item['job_id'].lstrip('~') }"],
            )
            for item in candidates
        ],
        "evidence_sha256": artifacts,
    }
    state["negotiation_intents"] = []
    for head in inbox_reconciliation["heads"]:
        if head["kind"] != "message_room" or head["changed"] is not True:
            continue
        intent = await asyncio.to_thread(
            plan_negotiation, head["resource_id"], inbox=inbox_ledger,
            loop_state_value=state,
            evidence_dir=DEFAULT_NEGOTIATION_EVIDENCE / head["event_id"],
        )
        state["negotiation_intents"].append({
            "room_id": head["resource_id"], "event_id": head["event_id"],
            "head_sha256": head["head_sha256"], "revision": head["revision"],
            "decision": intent["decision"], "reason_codes": intent["reason_codes"],
            "intent_sha256": intent["intent_sha256"],
        })
    inbound = plan_zero_connect_inbound(state)
    if inbound is not None:
        state["can_submit_public_job"] = False
        if inbound["state"] in {"invitation_detected", "direct_offer_detected"}:
            detail_artifact = Path(await navigate_and_snapshot(
                pass_id, f"{len(targets) + 1:02d}-1", "inbound-detail",
                inbound["resource_url"], "read_only", 2, 1440,
            ))
            detail_text, detail_hash, detail_links = _read_evidence(
                detail_artifact, inbound["resource_url"],
            )
            state["evidence_sha256"]["inbound-detail"] = detail_hash
            detail_state = parse_zero_connect_detail(inbound["state"], detail_text)
            state["free_acquisition"] = {
                **inbound,
                "detail_state": detail_state,
                "detail_evidence_sha256": detail_hash,
            }
            if inbound["state"] == "direct_offer_detected":
                offer_reconciliation = append_changed_heads(inbox_ledger, [normalize_observation(
                    kind="offer", resource_id=inbound["resource_id"],
                    resource_url=inbound["resource_url"], rendered_text=detail_text,
                    source_evidence_sha256=detail_hash, observed_at=state["observed_at"],
                    rendered_links=detail_links,
                )])
                state["inbox_reconciliation"] = {
                    "observed": inbox_reconciliation["observed"] + offer_reconciliation["observed"],
                    "appended": inbox_reconciliation["appended"] + offer_reconciliation["appended"],
                    "heads": inbox_reconciliation["heads"] + offer_reconciliation["heads"],
                }
            if detail_state == "actionable" and inbound["state"] == "invitation_detected":
                packet_sha = seal_inbound_detail(
                    inbound, detail_text, detail_hash, inbound_dir, state["observed_at"],
                )
                state["free_acquisition"]["private_packet_sha256"] = packet_sha
                proposal = await asyncio.to_thread(
                    plan_inbound, inbound_dir.expanduser() / f"{packet_sha}.json",
                    evidence_dir=inbound_evidence.expanduser() / packet_sha,
                )
                if proposal is None:
                    state["free_acquisition"]["proposal_state"] = "model_skip"
                else:
                    write_sealed_proposal(proposal, inbound_proposals)
                    acquisition, post_connects, post_hash = await execute_sealed_proposal(
                        proposal, pass_id=pass_id, sequence=len(targets) + 2,
                        database=database, manifest=manifest, browser_profile=browser_profile,
                    )
                    state["free_acquisition"].update(acquisition)
                    if post_connects is not None and post_hash is not None:
                        state.update(post_connects)
                        state["evidence_sha256"]["connects-post"] = post_hash
            elif detail_state == "actionable":
                packet_sha = seal_inbound_detail(
                    inbound, detail_text, detail_hash, inbound_dir, state["observed_at"],
                )
                state["free_acquisition"]["private_packet_sha256"] = packet_sha
                decision = await asyncio.to_thread(
                    qualify_direct_offer, inbound_dir.expanduser() / f"{packet_sha}.json",
                    evidence_dir=DEFAULT_OFFER_EVIDENCE.expanduser() / packet_sha,
                )
                state["free_acquisition"]["offer_state"] = {
                    "accept": "accept_ready",
                    "request_changes": "request_changes",
                    "decline": "decline",
                }[decision["action"]]
                state["free_acquisition"]["offer_reason_codes"] = decision["reason_codes"]
                if decision["action"] == "accept":
                    state["free_acquisition"].update(await execute_direct_offer(
                        decision, database=database, manifest=manifest,
                        browser_profile=browser_profile,
                    ))
        else:
            state["free_acquisition"] = inbound
        return state
    selected = plan_free_proposal(state, proposals_dir)
    state["can_submit_public_job"] = selected is not None
    if selected is None:
        state["free_acquisition"] = {"state": "waiting_free_capacity"}
    else:
        acquisition, post_connects, post_hash = await execute_sealed_proposal(
            selected, pass_id=pass_id, sequence=len(targets) + 1,
            database=database, manifest=manifest, browser_profile=browser_profile,
        )
        state["free_acquisition"] = acquisition
        if post_connects is not None and post_hash is not None:
            state.update(post_connects)
            state["evidence_sha256"]["connects-post"] = post_hash
    return state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cdp-base", default="http://127.0.0.1:9233")
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--proposals", type=Path, default=DEFAULT_PROPOSALS)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--browser-profile", type=Path, default=DEFAULT_BROWSER_PROFILE)
    parser.add_argument("--inbound-dir", type=Path, default=DEFAULT_INBOUND_DIR)
    parser.add_argument("--inbound-proposals", type=Path, default=DEFAULT_INBOUND_PROPOSALS)
    parser.add_argument("--inbound-evidence", type=Path, default=DEFAULT_INBOUND_EVIDENCE)
    parser.add_argument("--inbox-ledger", type=Path, default=DEFAULT_INBOX_LEDGER)
    parser.add_argument("--transitions", type=Path, default=DEFAULT_TRANSITIONS)
    parser.add_argument(
        "--output", type=Path,
        default=Path(os.path.expanduser("~/gig/state/upwork-free-loop.json")),
    )
    args = parser.parse_args()
    os.environ["CLOAK_CDP_BASE_URL"] = args.cdp_base.rstrip("/")
    state = asyncio.run(observe(
        args.candidates.expanduser(), args.proposals.expanduser(), args.database.expanduser(),
        args.manifest.expanduser(), args.browser_profile.expanduser(), args.inbound_dir.expanduser(),
        args.inbound_proposals.expanduser(), args.inbound_evidence.expanduser(),
        args.inbox_ledger.expanduser(),
    ))
    state = reconcile_terminal_transitions(
        args.output.expanduser(), args.transitions.expanduser(), state,
    )
    print(json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
