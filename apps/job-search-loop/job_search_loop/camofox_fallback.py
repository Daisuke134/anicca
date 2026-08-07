"""Authorize an isolated CamoFox recovery without transferring browser ownership."""

from __future__ import annotations

import hashlib


CAMOFOX_ENDPOINT = "http://127.0.0.1:9378"


def _required(value: str, name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{name} is required")
    return normalized


def authorize_camofox_fallback(
    *,
    application_id: str,
    intent_id: str,
    fence: int,
    classification: str,
    click_phase: str,
    transport_phase: str,
) -> dict[str, object]:
    """Return a tenant-isolated session receipt only for a pre-click fingerprint block."""
    application_id = _required(application_id, "application_id")
    intent_id = _required(intent_id, "intent_id")
    if not isinstance(fence, int) or isinstance(fence, bool) or fence < 1:
        raise ValueError("fence must be a positive integer")
    if classification != "fingerprint_rejected":
        raise ValueError("CamoFox requires a measured fingerprint rejection")
    if click_phase != "pre_click":
        raise ValueError("clicked intent cannot transfer to CamoFox")
    if transport_phase != "pre_request":
        raise ValueError("request-started intent cannot transfer to CamoFox")

    material = f"{application_id}:{intent_id}:{fence}".encode("utf-8")
    session_key = "ats-" + hashlib.sha256(material).hexdigest()[:20]
    return {
        "version": 1,
        "status": "authorized",
        "application_id": application_id,
        "intent_id": intent_id,
        "fence": fence,
        "endpoint": CAMOFOX_ENDPOINT,
        "user_id": "job-hunter",
        "session_key": session_key,
        "source_browser_owner": "cloakbrowser",
        "target_browser_owner": "camofox",
        "transfer_live_tab": False,
        "telegram_required": True,
    }
