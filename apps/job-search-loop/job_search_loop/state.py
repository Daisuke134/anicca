from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, urlsplit, urlunsplit


class InvalidTransition(ValueError):
    pass


TRANSITIONS = {
    "discovered": frozenset({"qualified", "rejected"}),
    "qualified": frozenset({"materials_ready", "rejected"}),
    "materials_ready": frozenset({"submit_claimed", "rejected"}),
    "submit_claimed": frozenset(
        {"submitted", "submit_unknown", "not_submitted"}
    ),
    "not_submitted": frozenset({"submit_claimed", "rejected"}),
    "submitted": frozenset(
        {
            "recruiter_contact",
            "screening",
            "assessment",
            "interview",
            "rejected",
            "withdrawn",
            "offer",
        }
    ),
    "recruiter_contact": frozenset(
        {"screening", "assessment", "interview", "rejected", "withdrawn", "offer"}
    ),
    "screening": frozenset(
        {"assessment", "interview", "rejected", "withdrawn", "offer"}
    ),
    "assessment": frozenset(
        {"interview", "rejected", "withdrawn", "offer"}
    ),
    "interview": frozenset({"interview", "rejected", "withdrawn", "offer"}),
}


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def canonical_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit(
        (parsed.scheme.casefold(), parsed.netloc.casefold(), path, "", "")
    )


def ats_snapshot_matches_application(application_url: str, snapshot_url: str) -> bool:
    """Accept the same official page or its same-origin /application form route."""
    application_parts = urlsplit(application_url.strip())
    snapshot_parts = urlsplit(snapshot_url.strip())
    if not application_parts.scheme or not snapshot_parts.scheme:
        return False
    if application_parts.scheme.casefold() != snapshot_parts.scheme.casefold():
        return False
    if application_parts.netloc.casefold() != snapshot_parts.netloc.casefold():
        return False
    application_path = application_parts.path.rstrip("/") or "/"
    snapshot_path = snapshot_parts.path.rstrip("/") or "/"
    if snapshot_path not in {application_path, f"{application_path}/application"}:
        return False

    application_query = sorted(
        (key.casefold(), value)
        for key, value in parse_qsl(
            application_parts.query, keep_blank_values=True
        )
    )
    snapshot_query = sorted(
        (key.casefold(), value)
        for key, value in parse_qsl(snapshot_parts.query, keep_blank_values=True)
    )
    if application_query == snapshot_query:
        return True

    tracking_keys = {"gh_src", "ref", "referrer", "source"}

    def tracking_only(query: list[tuple[str, str]]) -> bool:
        return all(key.startswith("utm_") or key in tracking_keys for key, _ in query)

    return tracking_only(application_query) and tracking_only(snapshot_query)


def canonical_job_id(company: str, title: str, url: str) -> str:
    identity = "\n".join(
        (_normalize_text(company), _normalize_text(title), canonical_url(url))
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def validate_transition(from_state: str, to_state: str) -> None:
    if to_state not in TRANSITIONS.get(from_state, frozenset()):
        raise InvalidTransition(f"invalid transition: {from_state} -> {to_state}")
