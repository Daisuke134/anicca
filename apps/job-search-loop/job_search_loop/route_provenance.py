from __future__ import annotations

import hashlib
import re
from urllib.parse import urlsplit


class ProvenanceError(ValueError):
    pass


def _host_matches(host: str, domain: str) -> bool:
    normalized = domain.casefold().strip().strip(".")
    return bool(normalized) and (host == normalized or host.endswith(f".{normalized}"))


def _source_span(text: str, recipient: str) -> str:
    paragraphs = [part.strip() for part in re.split(r"[\r\n]+", text) if part.strip()]
    for paragraph in paragraphs:
        sentences = [part.strip() for part in re.split(r"(?<=[.!?。！？])\s+", paragraph)]
        for sentence in sentences:
            if recipient.casefold() in sentence.casefold():
                return " ".join(sentence.split())
    raise ProvenanceError("recipient is absent from official source text")


def verify_recipient_route(
    *,
    source_url: str,
    source_text: str,
    source_sha256: str,
    recipient: str,
    employer_domains: list[str],
    official_provider_domains: list[str],
) -> dict[str, str]:
    parsed = urlsplit(source_url)
    host = (parsed.hostname or "").casefold()
    if parsed.scheme != "https" or not host:
        raise ProvenanceError("recipient source must be HTTPS")
    authorized_domains = [*employer_domains, *official_provider_domains]
    if not any(_host_matches(host, domain) for domain in authorized_domains):
        raise ProvenanceError("recipient source is not employer-controlled or approved")
    calculated = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    if calculated != source_sha256:
        raise ProvenanceError("recipient source hash does not match")
    normalized_recipient = recipient.casefold().strip()
    if re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", normalized_recipient) is None:
        raise ProvenanceError("recipient is not a valid public email address")
    span = _source_span(source_text, normalized_recipient)
    lowered = span.casefold()
    application_terms = (
        "apply",
        "application",
        "resume",
        "curriculum vitae",
        " cv ",
        "応募",
        "履歴書",
        "職務経歴書",
    )
    direction_terms = ("email", "send", "submit", "送", "メール")
    accepts = any(term in f" {lowered} " for term in application_terms) and any(
        term in lowered for term in direction_terms
    )
    return {
        "route_kind": "recruiting_email" if accepts else "recruiting_outreach",
        "recipient": normalized_recipient,
        "recipient_acceptance": "accepts_applications" if accepts else "outreach_only",
        "source_url": source_url,
        "source_sha256": source_sha256,
        "source_span": span,
    }


def verify_official_url_route(
    *,
    source_url: str,
    source_text: str,
    source_sha256: str,
    target_url: str,
    employer_domains: list[str],
    official_provider_domains: list[str],
) -> dict[str, str]:
    authorized_domains = [*employer_domains, *official_provider_domains]
    source = urlsplit(source_url)
    source_host = (source.hostname or "").casefold()
    if source.scheme != "https" or not any(
        _host_matches(source_host, domain) for domain in authorized_domains
    ):
        raise ProvenanceError("alternate route source is not authorized")
    if hashlib.sha256(source_text.encode("utf-8")).hexdigest() != source_sha256:
        raise ProvenanceError("alternate route source hash does not match")
    target = urlsplit(target_url)
    target_host = (target.hostname or "").casefold()
    if target.scheme != "https" or not any(
        _host_matches(target_host, domain) for domain in authorized_domains
    ):
        raise ProvenanceError("alternate route target is not authorized")
    if target_url not in source_text:
        raise ProvenanceError("alternate route target is absent from source")
    return {
        "route_kind": "alternate_official",
        "endpoint": target_url,
        "recipient_acceptance": "not_applicable",
        "source_url": source_url,
        "source_sha256": source_sha256,
    }
