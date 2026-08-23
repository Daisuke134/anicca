#!/usr/bin/env python3
"""Read-only Upwork job discovery and strict canonical normalization."""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Callable
from urllib.parse import urlsplit

from provider_adapter import (
    Opportunity, OpportunityDetail, ProviderReceipt, ProviderState, TransportAck,
)
try:
    from upwork_proposal import ProposalPayload, payload_sha256
except ModuleNotFoundError:
    from providers.upwork_proposal import ProposalPayload, payload_sha256


_JOB_KEYS = {
    "id", "url", "title", "description", "skills", "amount",
    "hourlyBudgetMin", "hourlyBudgetMax", "client", "activity", "connects", "jobStatus",
}
_CLIENT_KEYS = {
    "verificationStatus", "totalSpent", "totalHires", "totalPostedJobs",
    "totalReviews", "totalFeedback",
}
_ACTIVITY_KEYS = {"totalApplicants", "interviewing", "invitesSent", "lastClientActivity"}
_JOB_ID = re.compile(r"~[A-Za-z0-9]{10,64}")


class DiscoveryContractError(ValueError):
    """An Upwork read result is incomplete, stale, or unsafe to consume."""


@dataclass(frozen=True)
class UpworkOpportunity(Opportunity):
    scope: str
    skills: tuple[str, ...]
    pricing_kind: str
    minimum_minor: int
    maximum_minor: int
    client_evidence: tuple[tuple[str, Any], ...]
    activity: tuple[tuple[str, Any], ...]
    connects_cost: int


def _object(value: Any, keys: set[str], reason: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise DiscoveryContractError(reason)
    return value


def _integer(value: Any, reason: str) -> int:
    if type(value) is not int or value < 0:
        raise DiscoveryContractError(reason)
    return value


def _timestamp(value: Any, reason: str) -> str:
    if not isinstance(value, str):
        raise DiscoveryContractError(reason)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise DiscoveryContractError(reason) from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise DiscoveryContractError(reason)
    return value


def _minor(value: Any) -> int:
    if isinstance(value, bool):
        raise DiscoveryContractError("invalid_budget")
    try:
        cents = Decimal(str(value)) * 100
    except (InvalidOperation, ValueError):
        raise DiscoveryContractError("invalid_budget") from None
    if not cents.is_finite() or cents != cents.to_integral_value() or cents < 0:
        raise DiscoveryContractError("invalid_budget")
    return int(cents)


def _money(value: Any) -> tuple[int, str]:
    money = _object(value, {"rawValue", "currency"}, "invalid_budget")
    currency = money["currency"]
    if currency != "USD":
        raise DiscoveryContractError("unsupported_currency")
    return _minor(money["rawValue"]), currency


def _normalize_job(raw: Any, observed_at: str) -> UpworkOpportunity:
    job = _object(raw, _JOB_KEYS, "partial_job")
    observed_at = _timestamp(observed_at, "invalid_observed_at")
    job_id = job["id"]
    if not isinstance(job_id, str) or not _JOB_ID.fullmatch(job_id):
        raise DiscoveryContractError("invalid_job_id")
    url = job["url"]
    parsed = urlsplit(url) if isinstance(url, str) else None
    if not parsed or parsed.scheme != "https" or parsed.netloc != "www.upwork.com" or job_id not in parsed.path:
        raise DiscoveryContractError("invalid_job_url")
    if job["jobStatus"] != "OPEN":
        raise DiscoveryContractError("job_not_open")
    for field in ("title", "description"):
        if not isinstance(job[field], str) or not job[field].strip():
            raise DiscoveryContractError("partial_job")
    raw_skills = job["skills"]
    if not isinstance(raw_skills, list) or not raw_skills:
        raise DiscoveryContractError("partial_job")
    skills = tuple(
        _object(item, {"name"}, "partial_job")["name"] for item in raw_skills
    )
    if any(not isinstance(skill, str) or not skill.strip() for skill in skills):
        raise DiscoveryContractError("partial_job")
    if job["amount"] is not None:
        minimum, currency = _money(job["amount"])
        maximum, pricing = minimum, "fixed"
        if job["hourlyBudgetMin"] is not None or job["hourlyBudgetMax"] is not None:
            raise DiscoveryContractError("invalid_budget")
    else:
        minimum, currency = _money(job["hourlyBudgetMin"])
        maximum, maximum_currency = _money(job["hourlyBudgetMax"])
        if maximum_currency != currency or maximum < minimum:
            raise DiscoveryContractError("invalid_budget")
        pricing = "hourly"
    client = _object(job["client"], _CLIENT_KEYS, "partial_job")
    activity = _object(job["activity"], _ACTIVITY_KEYS, "partial_job")
    rating = client["totalFeedback"]
    if isinstance(rating, bool) or not isinstance(rating, (int, float)) or not 0 <= rating <= 5:
        raise DiscoveryContractError("invalid_client_evidence")
    client_evidence = (
        ("payment_verified", client["verificationStatus"] == "VERIFIED"),
        ("total_spent_minor", _money(client["totalSpent"])[0]),
        ("total_hires", _integer(client["totalHires"], "invalid_client_evidence")),
        ("jobs_posted", _integer(client["totalPostedJobs"], "invalid_client_evidence")),
        ("reviews", _integer(client["totalReviews"], "invalid_client_evidence")),
        ("rating", rating),
    )
    activity_evidence = (
        ("applicants", _integer(activity["totalApplicants"], "invalid_activity")),
        ("interviewing", _integer(activity["interviewing"], "invalid_activity")),
        ("invites_sent", _integer(activity["invitesSent"], "invalid_activity")),
        ("last_client_activity_at", _timestamp(activity["lastClientActivity"], "invalid_activity")),
    )
    canonical = json.dumps(job, sort_keys=True, separators=(",", ":"))
    return UpworkOpportunity(
        provider="upwork", opportunity_id=job_id, source_url=url, title=job["title"].strip(),
        currency=currency, source_hash=hashlib.sha256(canonical.encode()).hexdigest(),
        observed_at=observed_at, scope=job["description"].strip(), skills=skills,
        pricing_kind=pricing, minimum_minor=minimum, maximum_minor=maximum,
        client_evidence=client_evidence, activity=activity_evidence,
        connects_cost=_integer(job["connects"], "invalid_connects"),
    )


class UpworkAdapter:
    def __init__(
        self, transport: Any, read_page: Callable[..., dict[str, Any]],
        read_detail: Callable[..., dict[str, Any]], *, query: str,
        page_size: int = 20, max_pages: int = 5,
        effect_store: Any = None,
        read_connects: Callable[..., dict[str, Any]] | None = None,
        submit_proposal: Callable[..., TransportAck] | None = None,
        read_proposal: Callable[..., dict[str, Any] | None] | None = None,
        now_epoch: Callable[[], int] | None = None,
    ) -> None:
        if not query.strip() or not 1 <= page_size <= 50 or not 1 <= max_pages <= 20:
            raise DiscoveryContractError("invalid_discovery_bounds")
        self.transport, self.read_page, self.read_detail = transport, read_page, read_detail
        self.query, self.page_size, self.max_pages = query, page_size, max_pages
        self.effect_store = effect_store
        self.read_connects = read_connects
        self.submit_proposal = submit_proposal
        self.read_proposal = read_proposal
        self.now_epoch = now_epoch or (lambda: int(time.time()))

    def discover(self) -> list[UpworkOpportunity]:
        selection = self.transport.for_action("search")
        if selection is None:
            raise DiscoveryContractError("no_authorized_transport")
        cursor = None
        seen_cursors: set[str] = set()
        found: list[UpworkOpportunity] = []
        seen_jobs: set[str] = set()
        for page_number in range(self.max_pages):
            page = _object(
                self.read_page(selection, self.query, cursor, self.page_size),
                {"observedAt", "edges", "pageInfo"}, "invalid_page",
            )
            if not isinstance(page["edges"], list) or len(page["edges"]) > self.page_size:
                raise DiscoveryContractError("invalid_page")
            for edge in page["edges"]:
                node = _object(edge, {"cursor", "node"}, "invalid_page")["node"]
                job = _normalize_job(node, page["observedAt"])
                if job.opportunity_id in seen_jobs:
                    raise DiscoveryContractError("stale_job_identity")
                seen_jobs.add(job.opportunity_id)
                found.append(job)
            info = _object(page["pageInfo"], {"endCursor", "hasNextPage"}, "invalid_page")
            if info["hasNextPage"] is False:
                return found
            next_cursor = info["endCursor"]
            if not isinstance(next_cursor, str) or not next_cursor or next_cursor in seen_cursors:
                raise DiscoveryContractError("cursor_not_advancing")
            seen_cursors.add(next_cursor)
            cursor = next_cursor
        raise DiscoveryContractError("pagination_bound_exceeded")

    def inspect(self, opportunity_id: str) -> OpportunityDetail:
        selection = self.transport.for_action("inspect")
        if selection is None:
            raise DiscoveryContractError("no_authorized_transport")
        result = _object(
            self.read_detail(selection, opportunity_id), {"observedAt", "job"}, "invalid_detail",
        )
        job = _normalize_job(result["job"], result["observedAt"])
        if job.opportunity_id != opportunity_id:
            raise DiscoveryContractError("stale_job_identity")
        return OpportunityDetail(job, job.scope, job.source_hash)

    def _effect_dependencies(self) -> None:
        if (
            self.effect_store is None or not callable(self.read_connects)
            or not callable(self.submit_proposal) or not callable(self.read_proposal)
        ):
            raise DiscoveryContractError("proposal_effect_not_configured")

    def _selection(self, intent: Any):
        selection = self.transport.for_action("propose")
        authorization = getattr(selection, "authorization", None)
        if (
            selection is None
            or getattr(authorization, "receipt_hash", None) != intent.authorization_hash
        ):
            raise DiscoveryContractError("authorization_not_approved")
        return selection

    @staticmethod
    def _connects(value: Any) -> tuple[int, str]:
        if not isinstance(value, dict) or set(value) != {"balance", "observed_at", "evidence_hash"}:
            raise DiscoveryContractError("invalid_connects_readback")
        balance = value["balance"]
        if type(balance) is not int or balance < 0:
            raise DiscoveryContractError("invalid_connects_readback")
        _timestamp(value["observed_at"], "invalid_connects_readback")
        digest = value["evidence_hash"]
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise DiscoveryContractError("invalid_connects_readback")
        return balance, digest

    def plan_effect(self, action: str, payload: dict[str, Any] | ProposalPayload):
        self._effect_dependencies()
        if action != "propose" or not isinstance(payload, ProposalPayload):
            raise DiscoveryContractError("invalid_proposal_effect")
        if payload.provider != "upwork" or payload.payload_hash != payload_sha256(payload):
            raise DiscoveryContractError("invalid_proposal_payload")
        selection = self.transport.for_action("propose")
        if selection is None:
            raise DiscoveryContractError("authorization_not_approved")
        intent = self.transport.effect_intent(
            selection, resource_id=payload.opportunity_id, payload_hash=payload.payload_hash,
        )
        if self.effect_store.provider_effect(intent) is not None:
            self.effect_store.prepare_provider_effect(
                intent, authorization=selection.authorization, now=self.now_epoch(),
            )
            return intent
        connects_pre, connects_hash = self._connects(self.read_connects(selection))
        if connects_pre < payload.connects_cost:
            raise DiscoveryContractError("insufficient_free_connects")
        body = json.dumps(asdict(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.effect_store.prepare_provider_effect(
            intent, authorization=selection.authorization, now=self.now_epoch(),
            connects_pre=connects_pre, connects_pre_hash=connects_hash, payload_body=body,
        )
        return intent

    def _provider_readback(self, intent: Any, selection: Any) -> dict[str, Any] | None:
        value = self.read_proposal(selection, intent)
        if value is None:
            return None
        keys = {
            "proposal_id", "job_id", "payload_hash", "state", "connects_balance",
            "observed_at", "evidence_hash",
        }
        if not isinstance(value, dict) or set(value) != keys:
            raise DiscoveryContractError("invalid_proposal_readback")
        if (
            not isinstance(value["proposal_id"], str) or not value["proposal_id"]
            or value["job_id"] != intent.resource_id
            or value["payload_hash"] != intent.payload_hash
            or value["state"] != "submitted"
        ):
            raise DiscoveryContractError("invalid_proposal_readback")
        if type(value["connects_balance"]) is not int or value["connects_balance"] < 0:
            raise DiscoveryContractError("invalid_proposal_readback")
        _timestamp(value["observed_at"], "invalid_proposal_readback")
        if not isinstance(value["evidence_hash"], str) or not re.fullmatch(
            r"[0-9a-f]{64}", value["evidence_hash"],
        ):
            raise DiscoveryContractError("invalid_proposal_readback")
        return value

    def reconcile(self, intent: Any) -> ProviderState:
        self._effect_dependencies()
        row = self.effect_store.provider_effect(intent)
        if row is None:
            raise DiscoveryContractError("proposal_intent_missing")
        if row["reconciliation_state"] == "verified":
            return ProviderState(
                "upwork", intent.resource_id, "propose", "submitted",
                datetime.fromtimestamp(row["updated_at"], tz=timezone.utc).isoformat(),
                row["readback_hash"],
            )
        selection = self._selection(intent)
        readback = self._provider_readback(intent, selection)
        if readback is not None:
            self.effect_store.verify_provider_effect(
                intent, proposal_id=readback["proposal_id"],
                connects_post=readback["connects_balance"],
                readback_hash=readback["evidence_hash"], now=self.now_epoch(),
            )
            return ProviderState(
                "upwork", intent.resource_id, "propose", "submitted",
                readback["observed_at"], readback["evidence_hash"],
            )
        state = "absent" if row["state"] == "prepared" else "reconcile_unknown"
        return ProviderState(
            "upwork", intent.resource_id, "propose", state,
            datetime.fromtimestamp(row["updated_at"], tz=timezone.utc).isoformat(),
            row["connects_pre_hash"],
        )

    def execute(self, intent: Any) -> TransportAck:
        self._effect_dependencies()
        state = self.reconcile(intent)
        if state.state == "submitted":
            row = self.effect_store.provider_effect(intent)
            return TransportAck("upwork", "propose", intent.effect_key, True, row["proposal_id"])
        row = self.effect_store.provider_effect(intent)
        if row["state"] != "prepared":
            return TransportAck("upwork", "propose", intent.effect_key, False, None)
        selection = self._selection(intent)
        try:
            payload = json.loads(row["payload_body"])
        except (TypeError, json.JSONDecodeError) as exc:
            raise DiscoveryContractError("invalid_durable_proposal") from exc
        try:
            durable_payload = ProposalPayload(**payload)
        except (TypeError, ValueError) as exc:
            raise DiscoveryContractError("invalid_durable_proposal") from exc
        if (
            durable_payload.payload_hash != intent.payload_hash
            or payload_sha256(durable_payload) != intent.payload_hash
        ):
            raise DiscoveryContractError("invalid_durable_proposal")
        connects_now, _ = self._connects(self.read_connects(selection))
        if connects_now < durable_payload.connects_cost:
            raise DiscoveryContractError("insufficient_free_connects")
        started = self.effect_store.mark_provider_effect_started(
            intent, authorization=selection.authorization, now=self.now_epoch(),
        )
        if not started["started"]:
            return TransportAck("upwork", "propose", intent.effect_key, False, None)
        try:
            ack = self.submit_proposal(selection, intent, payload)
        except Exception:
            return TransportAck("upwork", "propose", intent.effect_key, False, None)
        if (
            not isinstance(ack, TransportAck) or ack.provider != "upwork"
            or ack.action != "propose" or ack.effect_key != intent.effect_key
        ):
            raise DiscoveryContractError("invalid_proposal_ack")
        return ack

    def readback(self, intent: Any) -> ProviderReceipt:
        state = self.reconcile(intent)
        if state.state != "submitted":
            raise DiscoveryContractError("proposal_readback_unconfirmed")
        row = self.effect_store.provider_effect(intent)
        return ProviderReceipt(
            provider="upwork", action="propose", effect_key=intent.effect_key,
            provider_receipt_id=row["proposal_id"], authoritative_state="submitted",
            observed_at=state.observed_at, evidence_hash=row["readback_hash"],
        )
