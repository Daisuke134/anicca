from __future__ import annotations

import hashlib
import re
from urllib.parse import urlsplit, urlunsplit


class InvalidTransition(ValueError):
    pass


DEFAULT_EMPLOYER_EXCLUSIONS = frozenset(
    {
        "Accenture",
        "KPMG",
        "Deloitte",
        "Ernst & Young",
        "EY",
        "PwC",
        "PricewaterhouseCoopers",
        "OpenAI",
        "Anthropic",
        "Palantir",
        "Cursor",
    }
)


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
            "email_sent",
            "recruiter_contact",
            "screening",
            "assessment",
            "interview",
            "rejected",
            "withdrawn",
            "offer",
        }
    ),
    # Legacy recruiting-outreach rows recorded a delivery-correction event
    # between the original submission and their later terminal reconciliation.
    # Keep that append-only history valid without reopening or retrying it.
    "email_sent": frozenset({"submit_unknown", "rejected", "withdrawn"}),
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


def is_excluded_employer(
    company: str, exclusions: frozenset[str] = DEFAULT_EMPLOYER_EXCLUSIONS
) -> bool:
    """Return true when a company matches a hard employer exclusion.

    Prefix matching covers ATS display names such as ``OpenAI Research`` while
    keeping unrelated names that merely contain an excluded word out.
    """
    normalized = _normalize_text(str(company))
    return any(
        normalized == _normalize_text(alias)
        or normalized.startswith(f"{_normalize_text(alias)} ")
        for alias in exclusions
        if _normalize_text(alias)
    )


def canonical_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    path = parsed.path.rstrip("/") or "/"
    hostname = parsed.netloc.casefold().split("@")[-1].split(":", 1)[0]
    segments = [segment for segment in path.split("/") if segment]
    # Ashby opens the same posting at `/company/job-id/application` after the
    # visible Apply CTA.  Keep the ATS form and posting as one dedupe identity;
    # other providers' paths remain untouched.
    if (
        hostname in {"jobs.ashbyhq.com", "app.ashbyhq.com"}
        and len(segments) >= 3
        and segments[-1].casefold() == "application"
    ):
        segments.pop()
        path = "/" + "/".join(segments)
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
