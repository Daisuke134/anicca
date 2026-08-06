"""Safe normalization boundary for already-extracted career-site job rows.

This contract is informed by ApplyPilot SmartExtract, but executes no selectors,
scripts, browser actions, LLM plans, or persistence and copies no upstream source.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import urljoin, urlsplit

from .state import canonical_url


EXECUTABLE_PLAN_KEYS = frozenset({"selector", "selectors", "script", "javascript", "extraction"})


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
        company = str(value.get("company") or value.get("hiringOrganization") or "").strip()
        if company:
            row["company"] = company
        results.append(row)
    return {
        "results": results,
        "accepted_count": accepted_total,
        "rejected_count": rejected,
        "truncated": accepted_total > len(results),
    }
