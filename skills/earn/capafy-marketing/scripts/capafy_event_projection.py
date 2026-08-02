#!/usr/bin/env python3
"""Fold the canonical Capafy event ledger into one deterministic public projection."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import re
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from capafy_event_store import MONEY_FIELDS, read_events, validate_event


ZERO = Decimal("0.00")
INVENTORY_STATES = {
    "online": "online",
    "approved": "online",
    "under_review": "under_review",
    "submitted": "under_review",
    "draft": "draft",
    "rejected": "rejected",
    "review_rejected": "rejected",
    "banned": "rejected",
}


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def _money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):.2f}"


def _url_for_host(urls: list[str], host_suffix: str) -> str | None:
    for url in urls:
        host = (urlparse(url).hostname or "").lower()
        if host == host_suffix or host.endswith(f".{host_suffix}"):
            return url
    return None


def _account_projection(event: dict | None) -> dict:
    if event is None:
        return {
            "handle": "no-active-account",
            "lifecycle_status": "unknown",
            "capability": "none",
            "session_established": False,
            "post_write_session_verified": False,
            "account_status": "unknown",
        }
    event_type = event["event_type"]
    status = event["status"]["after"] or "unknown"
    session_established = event_type in {
        "account.session_ready",
        "account.publish_probe_ready",
        "account.post_verified",
        "account.commercial_ready",
    }
    capability = "publish_probe" if event_type == "account.publish_probe_ready" else "none"
    if event_type == "account.commercial_ready":
        capability = "commercial_post"
    if event_type == "account.post_verified":
        status = "reach_observing"
    return {
        "handle": event["entity"]["id"],
        "lifecycle_status": status,
        "capability": capability,
        "session_established": session_established,
        "post_write_session_verified": event_type in {"account.post_verified", "account.commercial_ready"},
        "account_status": "clean",
    }


def _label_value(labels: list[str], prefix: str) -> str | None:
    for label in labels:
        if label.startswith(prefix):
            return label[len(prefix):]
    return None


def _experiment_projection(event: dict | None) -> dict | None:
    if event is None:
        return None
    labels = event["public_evidence"]["labels"]
    summary = event["summary"]
    model_match = re.fullmatch(
        r"(?:Activated|Stopped) (?:one )?bounded ([a-z_]+) packaging experiment for seller-owned product ([0-9]+)",
        summary,
    )
    purchase_model = model_match.group(1) if model_match else "unknown"
    agent_id = event.get("correlation_id") or (model_match.group(2) if model_match else "unknown")
    price = _label_value(labels, "price hypothesis $")
    projected = _label_value(labels, "projected contribution $")
    if projected and ";" in projected:
        projected = projected.split(";", 1)[0]
    observed = _label_value(labels, "observed contribution $")
    public_url = next(
        (
            url for url in event["public_evidence"]["urls"]
            if _url_for_host([url], "capafy.ai")
            and urlparse(url).path.rstrip("/").endswith(f"/{agent_id}")
        ),
        None,
    )
    return {
        "experiment_id": event["entity"]["id"],
        "agent_id": agent_id,
        "owner": event["next"]["owner"],
        "status": event["status"]["after"],
        "purchase_model": purchase_model,
        "price_usd": price,
        "projected_contribution_usd": projected,
        "observed_contribution_usd": observed,
        "success_metric": _label_value(labels, "success metric: "),
        "stop_condition": _label_value(labels, "stop condition: "),
        "stop_reason": _label_value(labels, "stop reason: "),
        "public_url": public_url,
    }


def project_company(events: list[dict]) -> dict:
    """Validate and fold events in ledger order without consulting legacy state."""

    seen: set[str] = set()
    money = {field: ZERO for field in MONEY_FIELDS}
    orders = 0
    listings: dict[str, dict] = {}
    accounts: dict[str, tuple[int, dict]] = {}
    content_snapshots: dict[str, dict] = {}
    latest_publication: dict | None = None
    incident_states: dict[str, tuple[int, dict]] = {}
    experiment_states: dict[str, tuple[int, dict]] = {}

    for index, event in enumerate(events):
        errors = validate_event(event)
        if errors:
            raise ValueError(
                f"invalid event at index {index}: {'; '.join(errors)}"
            )
        event_id = event["event_id"]
        if event_id in seen:
            raise ValueError(f"duplicate event_id: {event_id}")
        seen.add(event_id)

        for field in MONEY_FIELDS:
            money[field] += Decimal(event["money"][field])
        if event["event_type"] == "order.received":
            orders += int(event["metrics"].get("orders", 0))

        entity = event["entity"]
        if entity["type"] == "listing" and event["event_type"].startswith("listing."):
            listings[entity["id"]] = event
        if entity["type"] == "account" and event["event_type"].startswith("account."):
            accounts[entity["id"]] = (index, event)
        if event["event_type"] == "content.published":
            latest_publication = event
        if event["event_type"] == "content.measured":
            content_snapshots[entity["id"]] = event
        if event["event_type"].startswith("incident."):
            incident_states[entity["id"]] = (index, event)
        if entity["type"] == "experiment" and event["event_type"].startswith("experiment."):
            experiment_states[entity["id"]] = (index, event)

    inventory = {"online": 0, "under_review": 0, "draft": 0, "rejected": 0}
    for event in listings.values():
        bucket = INVENTORY_STATES.get(str(event["status"]["after"] or ""))
        if bucket:
            inventory[bucket] += 1

    metrics: dict[str, int] = {}
    for event in content_snapshots.values():
        for field, value in event["metrics"].items():
            metrics[field] = metrics.get(field, 0) + value

    latest_account = max(accounts.values(), default=None, key=lambda item: item[0])
    account = _account_projection(latest_account[1] if latest_account else None)

    publication_urls = (
        latest_publication["public_evidence"]["urls"]
        if latest_publication is not None
        else []
    )
    public_post_url = _url_for_host(publication_urls, "instagram.com")
    marketing_listing_url = _url_for_host(publication_urls, "capafy.ai")
    campaign_url = _url_for_host(publication_urls, "capafy-skills-daily.netlify.app")
    fallback_listing = next(
        (
            url
            for event in reversed(list(listings.values()))
            for url in event["public_evidence"]["urls"]
            if _url_for_host([url], "capafy.ai")
        ),
        None,
    )

    active_incidents = [
        item
        for item in incident_states.values()
        if item[1]["event_type"] != "incident.verified"
    ]
    latest_incident = max(active_incidents, default=None, key=lambda item: item[0])
    incident = None
    if latest_incident is not None:
        event = latest_incident[1]
        incident = {
            "incident_id": event["entity"]["id"],
            "owner": event["loop"],
            "summary": event["summary"],
            "phase": event["status"]["after"],
            "next_retry_at": event["next"]["retry_at"],
        }
    latest_experiment = max(experiment_states.values(), default=None, key=lambda item: item[0])
    experiment = _experiment_projection(latest_experiment[1] if latest_experiment else None)
    if experiment is not None:
        current_listing = listings.get(experiment["agent_id"])
        if current_listing is not None:
            experiment["public_url"] = (
                next(
                    (
                        url
                        for url in current_listing["public_evidence"]["urls"]
                        if _url_for_host([url], "capafy.ai")
                        and urlparse(url).path.rstrip("/").endswith(
                            f"/{experiment['agent_id']}"
                        )
                    ),
                    None,
                )
                if current_listing["status"]["after"] == "online"
                else None
            )

    as_of = events[-1]["recorded_at"] if events else "1970-01-01T00:00:00Z"
    company = {
        "schema_version": 1,
        "kind": "company_state",
        "as_of": as_of,
        "date": as_of[:10],
        "last_event_id": events[-1]["event_id"] if events else None,
        "inventory": inventory,
        "gross_usd": _money(money["gross_delta"]),
        "pending_usd": _money(money["pending_delta"]),
        "realized_usd": _money(money["realized_delta"]),
        "mrr_usd": _money(money["mrr_delta"]),
        "cost_usd": _money(money["cost_delta"]),
        "contribution_usd": _money(money["contribution_delta"]),
        "orders": orders,
        "account": account,
        "marketing": {
            "state": latest_publication["status"]["after"]
            if latest_publication
            else "not_published",
            "public_post_url": public_post_url,
            "campaign_url": campaign_url,
        },
        "metrics": metrics,
        "incident": incident,
        "experiment": experiment,
        "listing_url": marketing_listing_url or fallback_listing,
        "dashboard_url": "https://capafy-skills-daily.netlify.app/company/",
    }
    identity_input = {
        "event_ids": [event["event_id"] for event in events],
        "projection": company,
    }
    company["projection_id"] = "sha256:" + hashlib.sha256(
        _canonical(identity_input)
    ).hexdigest()
    return company


def projection_id(events: list[dict], projection: dict) -> str:
    """Return the identifier for a projection after verifying it matches the fold."""

    expected = project_company(events)
    if projection != expected:
        raise ValueError("projection does not match the supplied events")
    return expected["projection_id"]


def parity_errors(projected: dict, independent: dict) -> list[str]:
    """Compare ledger output with fresh source reads using public precision."""

    errors: list[str] = []
    money_fields = (
        "gross_usd",
        "pending_usd",
        "realized_usd",
        "mrr_usd",
        "cost_usd",
        "contribution_usd",
    )
    for field in money_fields:
        projected_value = _money(Decimal(str(projected.get(field, 0))))
        source_value = _money(Decimal(str(independent.get(field, 0))))
        if projected_value != source_value:
            errors.append(
                f"{field} mismatch: projection={projected_value!r} source={source_value!r}"
            )
    for field in ("inventory", "orders", "incident", "experiment"):
        if projected.get(field) != independent.get(field):
            errors.append(
                f"{field} mismatch: projection={projected.get(field)!r} "
                f"source={independent.get(field)!r}"
            )
    for field in (
        "handle",
        "lifecycle_status",
        "capability",
        "session_established",
        "post_write_session_verified",
        "account_status",
    ):
        projected_value = (projected.get("account") or {}).get(field)
        source_value = (independent.get("account") or {}).get(field)
        if projected_value != source_value:
            errors.append(
                f"account.{field} mismatch: projection={projected_value!r} "
                f"source={source_value!r}"
            )
    for field in ("state", "public_post_url", "campaign_url"):
        projected_value = (projected.get("marketing") or {}).get(field)
        source_value = (independent.get("marketing") or {}).get(field)
        if projected_value != source_value:
            errors.append(
                f"marketing.{field} mismatch: projection={projected_value!r} "
                f"source={source_value!r}"
            )
    return errors


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    project = commands.add_parser("project")
    project.add_argument("--ledger", type=Path, required=True)
    args = parser.parse_args()
    try:
        value = project_company(read_events(args.ledger))
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
