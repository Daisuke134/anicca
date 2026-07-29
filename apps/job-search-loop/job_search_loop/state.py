from __future__ import annotations

import hashlib
import re
from urllib.parse import urlsplit, urlunsplit


class InvalidTransition(ValueError):
    pass


TRANSITIONS = {
    "discovered": frozenset({"qualified", "rejected"}),
    "qualified": frozenset({"materials_ready", "rejected"}),
    "materials_ready": frozenset({"submit_claimed", "rejected"}),
    "submit_claimed": frozenset(
        {"submitted", "submit_unknown", "not_submitted"}
    ),
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


def canonical_job_id(company: str, title: str, url: str) -> str:
    identity = "\n".join(
        (_normalize_text(company), _normalize_text(title), canonical_url(url))
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def validate_transition(from_state: str, to_state: str) -> None:
    if to_state not in TRANSITIONS.get(from_state, frozenset()):
        raise InvalidTransition(f"invalid transition: {from_state} -> {to_state}")
