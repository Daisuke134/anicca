from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


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

DEDUP_STRIP_PARAMS = frozenset(
    {
        "language",
        "lang",
        "locale",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "ref",
        "src",
        "source",
        "gh_src",
        "lever-origin",
        "lever-source",
        "rltr",
    }
)


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def canonical_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    path = parsed.path.rstrip("/") or "/"
    identity_query = urlencode(
        sorted(
            (key, item)
            for key, item in parse_qsl(parsed.query, keep_blank_values=True)
            if key.casefold() not in DEDUP_STRIP_PARAMS
        ),
        doseq=True,
    )
    return urlunsplit(
        (parsed.scheme.casefold(), parsed.netloc.casefold(), path, identity_query, "")
    )


def canonical_job_id(company: str, title: str, url: str) -> str:
    identity = "\n".join(
        (_normalize_text(company), _normalize_text(title), canonical_url(url))
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def validate_transition(from_state: str, to_state: str) -> None:
    if to_state not in TRANSITIONS.get(from_state, frozenset()):
        raise InvalidTransition(f"invalid transition: {from_state} -> {to_state}")
