#!/usr/bin/env python3
"""Read-only publisher route identity and availability checks."""

from __future__ import annotations


def _handle(value) -> str:
    return str(value or "").strip().lower().lstrip("@")


def evaluate_route(account: dict, integrations: list[dict]) -> dict:
    blockers = []
    if account.get("status") != "approved_active":
        blockers.append(f"local account status is {account.get('status')}")
    integration_id = account.get("publisher_integration_id")
    matches = [row for row in integrations if row.get("id") == integration_id]
    if not matches:
        blockers.append("expected integration not found")
    elif len(matches) != 1:
        blockers.append("expected integration is not unique")
    else:
        remote = matches[0]
        if remote.get("identifier") != account.get("publisher_provider"):
            blockers.append("provider identifier mismatch")
        if _handle(remote.get("profile")) != _handle(account.get("native_handle")):
            blockers.append("native profile mismatch")
        if remote.get("disabled") is not False:
            blockers.append("Postiz integration is disabled")
    return {
        "schema_version": "marketing.publisher-route-status.v1",
        "account_id": account.get("account_id"),
        "integration_id": integration_id,
        "route_ready": not blockers,
        "blockers": blockers,
    }
