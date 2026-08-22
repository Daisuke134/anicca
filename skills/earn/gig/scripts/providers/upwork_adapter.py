#!/usr/bin/env python3
"""Read-only Upwork job discovery and strict canonical normalization."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Callable
from urllib.parse import urlsplit

from provider_adapter import Opportunity, OpportunityDetail


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
    ) -> None:
        if not query.strip() or not 1 <= page_size <= 50 or not 1 <= max_pages <= 20:
            raise DiscoveryContractError("invalid_discovery_bounds")
        self.transport, self.read_page, self.read_detail = transport, read_page, read_detail
        self.query, self.page_size, self.max_pages = query, page_size, max_pages

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
