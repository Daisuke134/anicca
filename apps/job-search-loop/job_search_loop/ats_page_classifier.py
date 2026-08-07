"""Bounded semantic hints for the adaptive resident ATS agent.

The classifier never executes browser actions and never confirms an application.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit


BLOCKED_SSO_HOSTS = (
    "accounts.google.com",
    "login.microsoftonline.com",
    "okta.com",
    "auth0.com",
)
CONFIRMATION_RE = re.compile(
    r"\b(?:application (?:has been )?submitted|application received|thank you for applying)\b",
    re.IGNORECASE,
)
CLOSED_RE = re.compile(
    r"\b(?:position|job|posting)\b.{0,40}\b(?:closed|filled|expired|no longer available)\b",
    re.IGNORECASE,
)
CAPTCHA_RE = re.compile(
    r"\b(?:captcha|verify (?:you are|that you are) human|security challenge|cloudflare challenge)\b",
    re.IGNORECASE,
)
SSO_RE = re.compile(
    r"\b(?:sign in|log in|continue) with (?:google|microsoft|okta|sso)\b|\bsingle sign[ -]on\b",
    re.IGNORECASE,
)
VALIDATION_RE = re.compile(
    r"\b(?:required field|field is required|this field is required|invalid|please (?:enter|select|complete))\b",
    re.IGNORECASE,
)
ACCOUNT_RE = re.compile(r"\b(?:create account|sign in|log in|password)\b", re.IGNORECASE)
APPLY_RE = re.compile(r"\b(?:apply|start application|apply for this job)\b", re.IGNORECASE)


def classify_execution_outcome(
    *,
    recaptcha_present: bool,
    visible_challenge: bool,
    fingerprint_rejected: bool,
    request_started: bool,
    authoritative_receipt: bool,
) -> dict[str, Any]:
    """Classify one fenced browser attempt without granting Submit authority."""
    flags = (
        recaptcha_present,
        visible_challenge,
        fingerprint_rejected,
        request_started,
        authoritative_receipt,
    )
    if any(not isinstance(value, bool) for value in flags):
        raise ValueError("execution outcome flags must be booleans")
    if authoritative_receipt and not request_started:
        raise ValueError("authoritative receipt requires a started request")
    if visible_challenge and fingerprint_rejected:
        raise ValueError("challenge and fingerprint rejection are mutually exclusive")

    if authoritative_receipt:
        classification = "confirmed_receipt"
        next_route = "complete_submitted"
    elif request_started:
        classification = "request_started_unknown"
        next_route = "complete_submit_unknown"
    elif visible_challenge:
        classification = "visible_challenge"
        next_route = "same_fence_captcha_recovery"
    elif fingerprint_rejected:
        classification = "fingerprint_rejected"
        next_route = "same_fence_camofox_recovery"
    elif recaptcha_present:
        classification = "invisible_recaptcha"
        next_route = "same_fence_continue_observation"
    else:
        classification = "no_anti_bot_signal"
        next_route = "same_fence_continue"

    return {
        "version": 1,
        "classification": classification,
        "next_route": next_route,
        "preserve_fence": True,
        "telegram_required": True,
        "application_confirmed": classification == "confirmed_receipt",
    }


def _bounded_controls(snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    controls: list[dict[str, Any]] = []
    frames = snapshot.get("frames")
    if not isinstance(frames, list):
        return controls
    for frame in frames[:20]:
        if not isinstance(frame, Mapping):
            continue
        frame_url = str(frame.get("url") or "")[:1_000]
        values = frame.get("controls")
        if not isinstance(values, list):
            continue
        for value in values[:500]:
            if not isinstance(value, Mapping):
                continue
            controls.append({
                "tag": str(value.get("tag") or "")[:40].casefold(),
                "type": str(value.get("type") or "")[:40].casefold(),
                "role": str(value.get("role") or "")[:40].casefold(),
                "text": " ".join(
                    str(value.get("text") or value.get("label") or "")[:1_000].split()
                ),
                "required": value.get("required") is True,
                "frame_url": str(value.get("frame_url") or frame_url)[:1_000],
            })
    return controls


def classify_ats_page(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Classify a passive semantic snapshot while leaving action choice to Terra."""
    if not isinstance(snapshot, Mapping):
        raise ValueError("semantic snapshot must be an object")
    page_url = str(snapshot.get("url") or "")[:2_000]
    parsed = urlsplit(page_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("semantic snapshot requires an HTTP(S) page URL")
    controls = _bounded_controls(snapshot)
    text = "\n".join(control["text"] for control in controls if control["text"])
    hostname = parsed.hostname.casefold()
    signals: list[str] = []

    if CONFIRMATION_RE.search(text) or re.search(r"/(?:thank-you|application-submitted)(?:/|$)", parsed.path, re.I):
        classification = "confirmation_like"
        next_route = "authoritative_confirmation_required"
        signals.append("confirmation_semantics")
    elif CLOSED_RE.search(text):
        classification = "closed_posting"
        next_route = "gmail_fallback_required"
        signals.append("closed_posting_text")
    elif CAPTCHA_RE.search(text):
        classification = "visible_captcha"
        next_route = "gmail_fallback_required"
        signals.append("visible_human_challenge")
    elif any(hostname == host or hostname.endswith(f".{host}") for host in BLOCKED_SSO_HOSTS) or SSO_RE.search(text):
        classification = "blocked_sso"
        next_route = "gmail_fallback_required"
        signals.append("blocked_sso_surface")
    elif VALIDATION_RE.search(text) or any(
        control["role"] == "alert" and control["text"] for control in controls
    ):
        classification = "validation_error"
        next_route = "terra_continue_formal"
        signals.append("visible_validation_error")
    elif any(control["type"] == "file" for control in controls) or (
        any(control["required"] for control in controls)
        and any(APPLY_RE.search(control["text"]) for control in controls)
    ):
        classification = "application_form"
        next_route = "terra_continue_formal"
        signals.append("application_controls")
    elif ACCOUNT_RE.search(text) or any(control["type"] == "password" for control in controls):
        classification = "account_auth"
        next_route = "terra_continue_formal"
        signals.append("account_controls")
    elif APPLY_RE.search(text):
        classification = "job_detail"
        next_route = "terra_continue_formal"
        signals.append("application_entry")
    else:
        classification = "unknown"
        next_route = "terra_inspect_then_gmail_fallback"
        signals.append("no_known_semantic_surface")

    return {
        "version": 1,
        "classification": classification,
        "next_route": next_route,
        "signals": signals,
        "application_confirmed": False,
        "control_count": len(controls),
    }
