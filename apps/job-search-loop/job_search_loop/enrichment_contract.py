"""Bounded enrichment receipts that cannot claim application success.

The extraction shape is informed by ApplyPilot's pinned SmartExtract/detail modules.
This independent boundary copies no upstream source and owns no browser or database.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

from .state import canonical_url


MAX_DESCRIPTION_CHARS = 4_000


def _canonical_http_url(value: Any, *, field: str, required: bool) -> str | None:
    text = str(value or "").strip()
    if not text and not required:
        return None
    parsed = urlsplit(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{field} must be an HTTP(S) URL")
    return canonical_url(text)


def build_enrichment_receipt(
    *,
    candidate_url: str,
    source_url: str,
    provider: str,
    extraction: Mapping[str, Any],
) -> dict[str, Any]:
    """Return evidence-only enrichment keyed to one existing canonical candidate."""
    canonical_candidate = _canonical_http_url(
        candidate_url, field="candidate_url", required=True
    )
    canonical_source = _canonical_http_url(source_url, field="source_url", required=True)
    provider_name = provider.strip()
    if not provider_name:
        raise ValueError("provider is required")
    if not isinstance(extraction, Mapping):
        raise ValueError("extraction must be an object")

    description = str(
        extraction.get("full_description") or extraction.get("description") or ""
    ).strip()[:MAX_DESCRIPTION_CHARS]
    try:
        application_url = _canonical_http_url(
            extraction.get("application_url"),
            field="application_url",
            required=False,
        )
    except ValueError:
        application_url = None

    digest_input = "\n".join(
        (canonical_candidate or "", canonical_source or "", provider_name, description)
    )
    return {
        "version": 1,
        "candidate_url": canonical_candidate,
        "source_url": canonical_source,
        "provider": provider_name,
        "full_description": description,
        "application_url": application_url,
        "content_sha256": hashlib.sha256(digest_input.encode("utf-8")).hexdigest(),
    }
