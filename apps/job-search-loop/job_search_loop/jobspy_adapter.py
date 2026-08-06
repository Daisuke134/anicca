"""Normalize JobSpy records into the existing Job Hunter candidate queue.

The input contract is informed by ApplyPilot's pinned JobSpy integration at
4a8d521f67f5139811c0a910ef37410f8e6d836a. This is an independent adapter;
no ApplyPilot source code is copied into this module.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import urlsplit

from .candidate_queue import CandidateQueue


def _text(value: Any) -> str:
    text = str(value or "").strip()
    return "" if text.lower() == "nan" else text


def _http_url(value: Any) -> str:
    url = _text(value)
    if not url:
        return ""
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return url


def _normalize_row(row: Any, *, query_family: str) -> dict[str, str] | None:
    if not isinstance(row, Mapping):
        return None
    title = _text(row.get("title"))
    company = _text(row.get("company"))
    direct_url = _http_url(row.get("job_url_direct"))
    listing_url = _http_url(row.get("job_url"))
    url = direct_url or listing_url
    if not title or not company or not url:
        return None
    site = _text(row.get("site")).lower() or "unknown"
    route = "official_direct" if direct_url else "listing"
    return {
        "url": url,
        "source": f"jobspy:{site}:{route}",
        "query_family": query_family,
        "company": company,
        "title": title,
    }


def ingest_jobspy_rows(
    queue: CandidateQueue,
    rows: Iterable[Any],
    *,
    query_family: str,
) -> dict[str, int]:
    """Validate JobSpy rows and persist valid candidates through one queue owner."""
    family = query_family.strip()
    if not family:
        raise ValueError("query_family is required")
    links: list[dict[str, str]] = []
    rejected = 0
    for row in rows:
        normalized = _normalize_row(row, query_family=family)
        if normalized is None:
            rejected += 1
        else:
            links.append(normalized)
    return {**queue.discover(links), "rejected_row_count": rejected}
