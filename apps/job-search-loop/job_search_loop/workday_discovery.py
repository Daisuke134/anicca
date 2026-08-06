"""Bounded Workday CXS discovery provider with no persistence ownership.

The public request/response contract is informed by ApplyPilot's pinned Workday
integration at 4a8d521f67f5139811c0a910ef37410f8e6d836a. No upstream source is copied.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from typing import Any
from urllib.parse import urlsplit

from .candidate_queue import CandidateQueue


SAFE_ID = re.compile(r"[A-Za-z0-9_-]+")
WORKDAY_SUFFIXES = (".myworkdayjobs.com", ".myworkdaysite.com")


def _validated_board(board: dict[str, str]) -> tuple[str, str, str, str]:
    company = str(board.get("company", "")).strip()
    base_url = str(board.get("base_url", "")).strip().rstrip("/")
    tenant = str(board.get("tenant", "")).strip()
    site_id = str(board.get("site_id", "")).strip()
    parsed = urlsplit(base_url)
    hostname = (parsed.hostname or "").lower()
    if (
        parsed.scheme != "https"
        or not any(hostname.endswith(suffix) for suffix in WORKDAY_SUFFIXES)
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("base_url must be a fixed HTTPS Workday host")
    if not company or SAFE_ID.fullmatch(tenant) is None or SAFE_ID.fullmatch(site_id) is None:
        raise ValueError("company, tenant, and site_id are required and must be safe")
    return company, base_url, tenant, site_id


def _posting_row(
    posting: Any,
    *,
    company: str,
    base_url: str,
    site_id: str,
) -> tuple[str, dict[str, Any] | None]:
    if not isinstance(posting, dict):
        return "malformed", None
    if posting.get("isListed") is False:
        return "inactive", None
    title = str(posting.get("title", "")).strip()
    external_path = str(posting.get("externalPath", "")).strip()
    parsed_path = urlsplit(external_path)
    if (
        not title
        or not external_path.startswith("/")
        or external_path.startswith("//")
        or parsed_path.scheme
        or parsed_path.netloc
        or ".." in parsed_path.path.split("/")
    ):
        return "malformed", None
    row: dict[str, Any] = {
        "title": title,
        "company": company,
        "url": f"{base_url}/{site_id}{external_path}",
        "location": str(posting.get("locationsText", "")).strip(),
        "source_kind": "official",
        "ats": "workday",
    }
    posted = str(posting.get("postedOn", "")).strip()
    if posted:
        row["posted"] = posted
    return "active", row


def search_workday_board(
    query: str,
    *,
    board: dict[str, str],
    request: Callable[..., Any],
    page_size: int = 20,
    max_pages: int = 5,
    max_results: int = 100,
) -> dict[str, Any]:
    """Search one fixed Workday tenant and return bounded official candidates."""
    search_text = query.strip()
    if not search_text:
        raise ValueError("query is required")
    if page_size <= 0 or page_size > 100 or max_pages <= 0 or max_results <= 0:
        raise ValueError("page and result bounds must be positive")
    company, base_url, tenant, site_id = _validated_board(board)
    endpoint = f"{base_url}/wday/cxs/{tenant}/{site_id}/jobs"
    results: list[dict[str, Any]] = []
    inactive = 0
    malformed = 0
    offset = 0
    total: int | None = None
    pages = 0

    while pages < max_pages and len(results) < max_results:
        payload = {
            "appliedFacets": {},
            "limit": page_size,
            "offset": offset,
            "searchText": search_text,
        }
        response = request(
            endpoint,
            payload=payload,
            timeout_seconds=12.0,
            follow_redirects=False,
        )
        if not isinstance(response, dict) or not isinstance(response.get("jobPostings"), list):
            raise ValueError("unexpected Workday CXS response")
        postings = response["jobPostings"]
        if total is None:
            raw_total = response.get("total", len(postings))
            total = raw_total if isinstance(raw_total, int) and raw_total >= 0 else len(postings)
        for posting in postings:
            classification, row = _posting_row(
                posting, company=company, base_url=base_url, site_id=site_id
            )
            if classification == "inactive":
                inactive += 1
            elif classification == "malformed":
                malformed += 1
            elif row is not None and len(results) < max_results:
                results.append(row)
        pages += 1
        offset += page_size
        if not postings or offset >= total:
            break

    return {
        "results": results,
        "inactive_count": inactive,
        "malformed_count": malformed,
        "page_count": pages,
        "truncated": total is not None and offset < total,
    }


def ingest_workday_boards(
    queue: CandidateQueue,
    query: str,
    *,
    query_family: str,
    boards: Iterable[dict[str, str]],
    request: Callable[..., Any],
    max_results_per_board: int = 100,
) -> dict[str, int]:
    """Search registered boards and persist active rows through the existing queue."""
    family = query_family.strip()
    if not family:
        raise ValueError("query_family is required")
    links: list[dict[str, str]] = []
    inactive = 0
    malformed = 0
    for board in boards:
        result = search_workday_board(
            query,
            board=board,
            request=request,
            max_results=max_results_per_board,
        )
        inactive += result["inactive_count"]
        malformed += result["malformed_count"]
        for row in result["results"]:
            links.append(
                {
                    "url": row["url"],
                    "source": f"official_workday:{row['company']}",
                    "query_family": family,
                    "company": row["company"],
                    "title": row["title"],
                }
            )
    return {
        **queue.discover(links),
        "inactive_count": inactive,
        "malformed_count": malformed,
    }
