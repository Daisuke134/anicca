#!/usr/bin/env python3
"""Fold the canonical Capafy event ledger into one deterministic public projection."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from capafy_event_store import MONEY_FIELDS, read_events, validate_event


ZERO = Decimal("0.00")
_MISSING = object()
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
SOURCE_EVENT_TYPES = {
    "money": {"order.received", "balance.reconciled", "payout.received"},
    "inventory": {"listing.submitted", "listing.approved", "listing.observed"},
    "account": {"account.created", "account.session_ready", "account.publish_probe_ready", "account.post_verified", "account.commercial_ready"},
    "marketing": {"content.published", "content.measured", "experiment.activated", "experiment.configured", "experiment.measured", "experiment.stopped"},
    "cost": {"cost.measured"},
}
INCIDENT_PHASE_ORDER = {"detected": 0, "repair_started": 1, "unresolved": 1, "repaired": 2, "verified": 3}


def _paid_orders_for_event(event: dict) -> int | None:
    gross = Decimal(event["money"]["gross_delta"])
    if gross < ZERO:
        return None
    orders = event["metrics"].get("orders", 0)
    explicit = event["metrics"].get("paid_orders", _MISSING)
    if explicit is not _MISSING:
        return explicit if isinstance(explicit, int) and not isinstance(explicit, bool) and 0 <= explicit <= orders else None
    return int(gross > ZERO) if orders == 1 else None


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def _money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):.2f}"


def _utc(value: str | datetime) -> datetime:
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None: raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def _incident_parity(incident: dict | None) -> tuple[bool, tuple | None]:
    if incident is None: return True, None
    try:
        if not {"incident_id", "owner", "summary", "phase", "next_retry_at"} <= incident.keys(): return False, None
        retry_at = incident.get("next_retry_at")
        if retry_at is not None and (not isinstance(retry_at, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})", retry_at)): return False, None
        retry_at = None if retry_at is None else _utc(retry_at).replace(microsecond=0)
    except (AttributeError, TypeError, ValueError): return False, None
    return True, tuple(incident.get(field) for field in ("incident_id", "owner", "summary", "phase")) + (retry_at,)


def _source_freshness(events: list[dict], reference_time: str | datetime | None) -> dict:
    reference = _utc(reference_time) if reference_time is not None else max((_utc(event["recorded_at"]) for event in events), default=_utc("1970-01-01T00:00:00Z"))
    result = {}
    for name, event_types in SOURCE_EVENT_TYPES.items():
        latest = max((event for event in events if event["event_type"] in event_types), default=None, key=lambda event: _utc(event["recorded_at"]))
        observed = _utc(latest["recorded_at"]) if latest else None
        age = reference - observed if observed else None
        result[name] = {"observed_at": latest["recorded_at"], "freshness": "fresh" if timedelta(0) <= age <= timedelta(hours=24) else "stale"} if latest else {"observed_at": None, "freshness": "unknown"}
    return result


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


def project_company(events: list[dict], reference_time: str | datetime | None = None) -> dict:
    """Validate and fold events in ledger order without consulting legacy state."""

    seen: set[str] = set()
    money = {field: ZERO for field in MONEY_FIELDS}
    orders = 0
    listings: dict[str, dict] = {}
    accounts: dict[str, tuple[int, dict]] = {}
    content_snapshots: dict[str, dict] = {}
    latest_publication: dict | None = None
    incident_states: dict[str, tuple[tuple[datetime, int, int], dict]] = {}
    experiment_states: dict[str, tuple[int, dict]] = {}
    paid_orders: int | None = 0
    sales_latest: dict[tuple[str, str], int] = {}

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
        if event["event_type"] == "order.received":
            source = event["source"]
            sales_latest[(source["producer"], source["source_id"])] = index

    for index, event in enumerate(events):
        if event["event_type"] == "order.received":
            source = event["source"]
            if sales_latest[(source["producer"], source["source_id"])] != index:
                continue
        for field in MONEY_FIELDS:
            money[field] += Decimal(event["money"][field])
        if event["event_type"] == "order.received":
            orders += int(event["metrics"].get("orders", 0))
            paid = _paid_orders_for_event(event)
            if paid_orders is not None:
                paid_orders = None if paid is None else paid_orders + paid

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
            phase = str(event["status"]["after"] or "")
            chronology = (
                _utc(event["occurred_at"]),
                INCIDENT_PHASE_ORDER.get(phase, -1),
                index,
            )
            prior = incident_states.get(entity["id"])
            if prior is None or chronology >= prior[0]:
                incident_states[entity["id"]] = (chronology, event)
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

    sources = _source_freshness(events, reference_time)

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
        "paid_orders": paid_orders,
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
        "sources": sources,
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
    projected_paid = projected.get("paid_orders", _MISSING)
    source_paid = independent.get("paid_orders", _MISSING)
    if projected_paid is _MISSING or source_paid is _MISSING:
        projected_label = "<missing>" if projected_paid is _MISSING else repr(projected_paid)
        source_label = "<missing>" if source_paid is _MISSING else repr(source_paid)
        errors.append(f"paid_orders missing: projection={projected_label} source={source_label}")
    elif projected_paid != source_paid:
        errors.append(f"paid_orders mismatch: projection={projected_paid} source={source_paid}")
    for field in ("inventory", "orders", "experiment"):
        if projected.get(field) != independent.get(field):
            errors.append(
                f"{field} mismatch: projection={projected.get(field)!r} "
                f"source={independent.get(field)!r}"
            )
    projected_incident = _incident_parity(projected.get("incident"))
    source_incident = _incident_parity(independent.get("incident"))
    if not all((projected_incident[0], source_incident[0], projected_incident[1] == source_incident[1])):
        errors.append(f"incident mismatch: projection={projected.get('incident')!r} source={independent.get('incident')!r}")
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
        value = project_company(read_events(args.ledger), reference_time=datetime.now(timezone.utc))
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
