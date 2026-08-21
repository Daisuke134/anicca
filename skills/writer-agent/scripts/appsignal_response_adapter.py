#!/usr/bin/env python3
"""Pure AppSignal form/email correlation adapter for the shared commercial core."""

from __future__ import annotations

from email.utils import getaddresses
from typing import Any
from urllib.parse import urlparse


def matches(record: dict[str, Any]) -> bool:
    host = (urlparse(str(record.get("official_program_url") or "")).hostname or "").lower()
    return bool(
        record.get("publisher") == "AppSignal"
        and host == "blog.appsignal.com"
        and str(record.get("application_id") or "").strip()
        and str(record.get("provider_submission_id") or "").strip()
        and str(record.get("application_status") or "").strip() == "SUBMITTED"
    )


def gmail_query(record: dict[str, Any]) -> str:
    recipient = str(record.get("response_recipient") or "").strip().lower()
    if not recipient or "@" not in recipient:
        raise ValueError("AppSignal response recipient is unavailable")
    return f"in:anywhere newer_than:90d to:({recipient})"


def correlates(record: dict[str, Any], message: dict[str, Any]) -> bool:
    recipient = str(record.get("response_recipient") or "").strip().lower()
    if not recipient:
        return False
    recipients = {
        address.lower()
        for _name, address in getaddresses([str(message.get("to") or "")])
        if address
    }
    return recipient in recipients


def transition_payload(record: dict[str, Any], message: dict[str, Any]) -> dict[str, str]:
    application_id = str(record.get("application_id") or "").strip()
    provider_submission_id = str(record.get("provider_submission_id") or "").strip()
    message_id = str(message.get("id") or "").strip()
    thread_id = str(message.get("thread_id") or "").strip()
    if not all((application_id, provider_submission_id, message_id, thread_id)):
        raise ValueError("AppSignal transition payload is incomplete")
    return {
        "application_id": application_id,
        "provider_submission_id": provider_submission_id,
        "gmail_message_id": message_id,
        "gmail_thread_id": thread_id,
    }
