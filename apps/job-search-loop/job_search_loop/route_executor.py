from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable

from .ledger import Ledger


TERMINAL_OR_LIVE = {"action_started", "delivered", "delivery_unknown", "replied"}
ATS_ROUTE_KINDS = {"canonical_ats", "alternate_official"}
EMAIL_ROUTE_KINDS = {"recruiting_email", "recruiting_outreach"}


def _sha256(path: Path) -> str:
    if not path.is_absolute() or not path.is_file():
        raise ValueError("route artifact must be an existing absolute file")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mark_unknown(
    ledger: Ledger, route_id: str, fence: int, reason: str
) -> dict[str, str]:
    evidence = json.dumps(
        {"route_id": route_id, "fence": fence, "reason": reason},
        sort_keys=True,
        separators=(",", ":"),
    )
    ledger.complete_application_route(
        route_id,
        fence=fence,
        state="delivery_unknown",
        provider_id=f"transport:unknown:{reason}",
        evidence_sha256=hashlib.sha256(evidence.encode("utf-8")).hexdigest(),
    )
    return {"status": "delivery_unknown", "route_id": route_id}


def execute_next_message_route(
    *,
    ledger: Ledger,
    application_id: str,
    actor: str,
    fence: int,
    message_path: Path,
    resume_path: Path,
    transport: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    routes = ledger.application_routes(application_id)
    if any(
        route["route_kind"] in EMAIL_ROUTE_KINDS
        and route["delivery_state"] in TERMINAL_OR_LIVE
        for route in routes
    ):
        return {"status": "cross_route_terminal"}
    if any(
        route["route_kind"] in ATS_ROUTE_KINDS
        and route["delivery_state"] in {"delivered", "replied"}
        for route in routes
    ):
        return {"status": "ats_confirmed"}
    eligible = [route for route in routes if route["delivery_state"] == "eligible"]
    if not eligible:
        return {"status": "no_eligible_route"}
    ats_attempted = any(
        route["route_kind"] in ATS_ROUTE_KINDS
        and route["delivery_state"] != "eligible"
        for route in routes
    )
    if not ats_attempted:
        browser_route = next(
            (route for route in eligible if route["route_kind"] in ATS_ROUTE_KINDS),
            None,
        )
        if browser_route is not None:
            return {
                "status": "browser_route_required",
                "route_id": browser_route["route_id"],
                "route_kind": browser_route["route_kind"],
            }
    route = next(
        (route for route in eligible if route["route_kind"] in EMAIL_ROUTE_KINDS),
        None,
    )
    if route is None:
        return {"status": "no_eligible_email_route"}
    if route["recipient_acceptance"] not in {
        "accepts_applications",
        "outreach_only",
    }:
        raise ValueError("message route recipient acceptance does not match route kind")
    message = Path(message_path).resolve()
    resume = Path(resume_path).resolve()
    message_sha256 = _sha256(message)
    resume_sha256 = _sha256(resume)
    route_id = str(route["route_id"])
    ledger.claim_application_route(
        route_id,
        actor=actor,
        fence=fence,
        message_path=str(message),
        message_sha256=message_sha256,
        resume_path=str(resume),
        resume_sha256=resume_sha256,
    )
    try:
        receipt = transport(
            recipient=str(route["endpoint"]),
            route_kind="recruiting_email",
            message_path=str(message),
            resume_path=str(resume),
            idempotency_key=f"{route_id}:{fence}",
        )
    except Exception as error:
        return _mark_unknown(ledger, route_id, fence, f"exception:{type(error).__name__}")
    if not isinstance(receipt, dict):
        return _mark_unknown(ledger, route_id, fence, "invalid_receipt_type")
    status = receipt.get("status")
    provider_id = receipt.get("provider_id")
    evidence_sha256 = receipt.get("evidence_sha256")
    if status not in {"delivered", "failed", "delivery_unknown"}:
        return _mark_unknown(ledger, route_id, fence, "invalid_receipt_status")
    if not isinstance(provider_id, str) or not provider_id.strip():
        return _mark_unknown(ledger, route_id, fence, "missing_provider_id")
    if not isinstance(evidence_sha256, str) or re.fullmatch(
        r"[0-9a-f]{64}", evidence_sha256
    ) is None:
        return _mark_unknown(ledger, route_id, fence, "invalid_evidence_sha256")
    ledger.complete_application_route(
        route_id,
        fence=fence,
        state=status,
        provider_id=provider_id,
        evidence_sha256=evidence_sha256,
    )
    return {"status": status, "route_id": route_id, "provider_id": provider_id}
