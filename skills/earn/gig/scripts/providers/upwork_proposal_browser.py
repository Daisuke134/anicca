#!/usr/bin/env python3
"""Fail-closed contracts for filling an Upwork proposal before any submit click."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any
from urllib.parse import urlsplit


_SNAPSHOT_KEYS = {
    "attachments", "bid_usd", "cover_letter", "delivery_days", "form_url",
    "job_id", "required_connects", "screening_answers", "submit_enabled",
    "submit_label", "validation_errors",
}


def validate_preflight(snapshot: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Require an exact filled-form readback and return no proposal copy."""
    if not isinstance(snapshot, dict) or set(snapshot) != _SNAPSHOT_KEYS:
        raise ValueError("upwork_proposal_preflight_mismatch")
    terms = payload.get("terms") if isinstance(payload, dict) else None
    if not isinstance(terms, dict):
        raise ValueError("upwork_proposal_preflight_mismatch")
    job_id = payload.get("job_id")
    url = urlsplit(str(snapshot.get("form_url") or ""))
    required = terms.get("required_connects")
    expected = {
        "job_id": job_id,
        "required_connects": required,
        "bid_usd": terms.get("bid_usd"),
        "delivery_days": terms.get("delivery_days"),
        "cover_letter": payload.get("cover_letter"),
        "screening_answers": payload.get("screening_answers"),
        "attachments": payload.get("attachments"),
    }
    if (
        not isinstance(job_id, str) or not job_id
        or url.scheme != "https" or url.netloc != "www.upwork.com"
        or f"/ab/proposals/job/{job_id}/apply" not in url.path
        or any(snapshot.get(key) != value for key, value in expected.items())
        or snapshot.get("submit_enabled") is not True
        or snapshot.get("validation_errors") != []
        or not isinstance(snapshot.get("submit_label"), str)
        or not re.search(rf"\b{required}\s+Connects\b", snapshot["submit_label"], re.IGNORECASE)
    ):
        raise ValueError("upwork_proposal_preflight_mismatch")
    evidence = hashlib.sha256(json.dumps(
        snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    return {
        "ready": True,
        "job_id": job_id,
        "required_connects": required,
        "evidence_sha256": evidence,
    }
