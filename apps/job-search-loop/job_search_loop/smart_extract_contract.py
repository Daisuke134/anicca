"""Safe normalization boundary for already-extracted career-site job rows.

This contract is informed by ApplyPilot SmartExtract, but executes no selectors,
scripts, browser actions, LLM plans, or persistence and copies no upstream source.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Any
from urllib.parse import quote_plus, urljoin, urlsplit

from .state import canonical_url

if TYPE_CHECKING:
    from .candidate_queue import CandidateQueue


EXECUTABLE_PLAN_KEYS = frozenset({"selector", "selectors", "script", "javascript", "extraction"})
SITE_PATTERN_BLOB_SHA = "5107aca850034334ad351b283e3694db989b2f8d"


def _location(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if not isinstance(value, Mapping):
        return ""
    address = value.get("address")
    if isinstance(address, Mapping):
        parts = [address.get("addressLocality"), address.get("addressRegion"), address.get("addressCountry")]
        return ", ".join(str(part).strip() for part in parts if str(part or "").strip())
    return ""


def _company(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        return str(value.get("name") or "").strip()
    return ""


def normalize_smart_extract_rows(
    rows: Iterable[Any],
    *,
    source_url: str,
    strategy: str,
    max_rows: int = 50,
) -> dict[str, Any]:
    """Normalize passive JSON rows without accepting executable extraction plans."""
    source = canonical_url(source_url)
    source_parts = urlsplit(source)
    strategy_name = strategy.strip()
    if source_parts.scheme not in {"http", "https"} or not source_parts.netloc:
        raise ValueError("source_url must be HTTP(S)")
    if strategy_name not in {"json_ld", "api_response"}:
        raise ValueError("unsupported passive extraction strategy")
    if max_rows <= 0 or max_rows > 50:
        raise ValueError("max_rows must be between 1 and 50")

    results: list[dict[str, Any]] = []
    rejected = 0
    accepted_total = 0
    for value in rows:
        if not isinstance(value, Mapping) or EXECUTABLE_PLAN_KEYS.intersection(value):
            rejected += 1
            continue
        title = str(value.get("title") or value.get("name") or "").strip()
        raw_url = str(value.get("url") or "").strip()
        if not raw_url:
            rejected += 1
            continue
        absolute_url = urljoin(source, raw_url)
        parsed = urlsplit(absolute_url)
        if not title or parsed.scheme not in {"http", "https"} or not parsed.netloc:
            rejected += 1
            continue
        accepted_total += 1
        if len(results) >= max_rows:
            continue
        result_url = canonical_url(absolute_url)
        row: dict[str, Any] = {
            "title": title,
            "url": result_url,
            "location": _location(value.get("jobLocation") or value.get("location")),
            "description": str(value.get("description") or "").strip()[:1_000],
            "source_kind": "official" if urlsplit(result_url).hostname == source_parts.hostname else "lead",
            "source_url": source,
            "discovery_provider": f"smart_extract:{strategy_name}",
        }
        company = _company(value.get("company") or value.get("hiringOrganization"))
        if company:
            row["company"] = company
        results.append(row)
    return {
        "results": results,
        "accepted_count": accepted_total,
        "rejected_count": rejected,
        "truncated": accepted_total > len(results),
    }


def build_site_targets(
    patterns: Mapping[str, Any], *, query: str, location: str
) -> dict[str, dict[str, str]]:
    """Expand only the pinned passive site registry into bounded HTTPS targets."""
    if patterns.get("source_blob_sha") != SITE_PATTERN_BLOB_SHA:
        raise ValueError("site pattern registry is not pinned to the adopted blob")
    sites = patterns.get("sites")
    if not isinstance(sites, list) or not sites or len(sites) > 20:
        raise ValueError("site pattern registry requires 1..20 sites")
    targets: dict[str, dict[str, str]] = {}
    for site in sites:
        if not isinstance(site, Mapping):
            raise ValueError("site pattern must be an object")
        site_id = str(site.get("id") or "").strip()
        template = str(site.get("url") or "").strip()
        site_type = str(site.get("type") or "").strip()
        if not site_id or site_id in targets or site_type not in {"search", "static"}:
            raise ValueError("invalid or duplicate site pattern")
        url = (
            template.replace("{query_encoded}", quote_plus(query.strip()))
            .replace("{location_encoded}", quote_plus(location.strip()))
        )
        if "{" in url or "}" in url:
            raise ValueError("unsupported site pattern placeholder")
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("site pattern must expand to HTTPS")
        targets[site_id] = {"url": url, "hostname": parsed.hostname}
    return targets


def ingest_site_pattern_captures(
    queue: "CandidateQueue",
    captures: Iterable[Any],
    *,
    patterns: Mapping[str, Any],
    query: str,
    location: str,
    query_family: str,
) -> dict[str, int]:
    """Route passive resident captures through SmartExtract and the one queue."""
    family = query_family.strip()
    if not family:
        raise ValueError("query_family is required")
    targets = build_site_targets(patterns, query=query, location=location)
    links: list[dict[str, str]] = []
    accepted = rejected = rejected_captures = 0
    for capture in captures:
        if not isinstance(capture, Mapping):
            rejected_captures += 1
            continue
        site_id = str(capture.get("site_id") or "").strip()
        source_url = str(capture.get("source_url") or "").strip()
        target = targets.get(site_id)
        if target is None or urlsplit(source_url).hostname != target["hostname"]:
            rejected_captures += 1
            continue
        rows = capture.get("rows")
        if not isinstance(rows, list):
            rejected_captures += 1
            continue
        try:
            normalized = normalize_smart_extract_rows(
                rows,
                source_url=source_url,
                strategy=str(capture.get("strategy") or ""),
            )
        except ValueError:
            rejected_captures += 1
            continue
        accepted += normalized["accepted_count"]
        rejected += normalized["rejected_count"]
        for row in normalized["results"]:
            links.append(
                {
                    "url": row["url"],
                    "source": (
                        f"site_pattern:{site_id}:{row['discovery_provider']}:"
                        f"{row['source_kind']}"
                    ),
                    "query_family": family,
                    "company": row.get("company", ""),
                    "title": row["title"],
                }
            )
    return {
        **queue.discover(links),
        "accepted_row_count": accepted,
        "rejected_row_count": rejected,
        "rejected_capture_count": rejected_captures,
    }
