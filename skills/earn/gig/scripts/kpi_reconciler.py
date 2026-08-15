#!/usr/bin/env python3
"""Project settled receipts into the common KPI contract without guessing a lane."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from kpi_contract import validate_kpi_record


JST = ZoneInfo("Asia/Tokyo")
SETTLED = {"検収", "支払", "検収完了", "completed", "paid"}
IDENTITY_KEYS = (
    "service_id", "service_version_hash", "opportunity_id", "application_id",
    "thread_id", "offer_id", "talkroom_id", "payment_receipt_id",
)
MAX_SAFE_INTEGER = 9007199254740991


class ReconciliationError(ValueError):
    pass


def _text(value: Any) -> str:
    return str(value or "").strip()


def _aliases(row: dict[str, Any], *keys: str) -> set[str]:
    values: set[str] = set()
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        if not isinstance(value, str):
            raise ReconciliationError("identity alias must be text")
        if value != value.strip():
            raise ReconciliationError("identity alias has surrounding whitespace")
        if value:
            values.add(value)
    return values


def _rfc3339(value: Any) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return dt.datetime.fromtimestamp(value, JST).isoformat(timespec="seconds")
        except (OverflowError, OSError, ValueError) as exc:
            raise ReconciliationError("settlement timestamp is invalid") from exc
    text = _text(value)
    parsed = None
    for fmt in ("%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            parsed = dt.datetime.strptime(text, fmt).replace(tzinfo=JST)
            break
        except ValueError:
            pass
    if parsed is None:
        try:
            parsed = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ReconciliationError("settlement timestamp is invalid") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=JST)
    return parsed.astimezone(JST).isoformat(timespec="seconds")


def _identity(**values: str | None) -> dict[str, str | None]:
    return {key: values.get(key) for key in IDENTITY_KEYS}


def verified_application_identities(
    applications: Iterable[dict[str, Any]],
) -> tuple[dict[str, set[str]], set[str]]:
    """Return the one Item-16 proof predicate shared by attribution and audits."""
    verified: dict[str, set[str]] = {}
    conflicts: set[str] = set()
    for row in applications:
        pass_ids = _aliases(row, "pass_id")
        requests = _aliases(row, "requestId", "request_id")
        if len(requests) > 1:
            conflicts.update(requests)
            continue
        pass_id = next(iter(pass_ids)) if len(pass_ids) == 1 else ""
        request = next(iter(requests)) if len(requests) == 1 else ""
        if (
            not pass_id or not request or row.get("status") != "applied"
            or row.get("submit_verified") is not True
            or row.get("applied_page_verified") is not True
            or "action" in row
        ):
            continue
        try:
            _rfc3339(row.get("ts"))
        except ReconciliationError:
            continue
        verified.setdefault(request, set()).add(
            f"gig:application:{pass_id}:{request}"
        )
    return verified, conflicts


def _lane_for(
    room: str,
    edges: list[dict[str, Any]],
    applications: dict[str, set[str]],
    ambiguous_requests: set[str],
) -> tuple[str, dict[str, str | None], str | None]:
    request_aliases = [_aliases(edge, "request_id", "opportunity_id") for edge in edges]
    request_ids = set().union(*request_aliases) if request_aliases else set()
    service_aliases = [
        (
            _aliases(edge, "service_id", "serviceId"),
            _aliases(edge, "service_version_hash", "serviceVersionHash"),
        ) for edge in edges
    ]
    service_fields_present = any(
        service_ids or version_hashes for service_ids, version_hashes in service_aliases
    )
    storefront_ids = {
        (next(iter(service_ids)), next(iter(version_hashes)))
        for service_ids, version_hashes in service_aliases
        if len(service_ids) == 1 and len(version_hashes) == 1
    }
    application_ids = applications.get(next(iter(request_ids)), set()) if (
        len(request_ids) == 1
    ) else set()
    conflict = (
        len(request_ids) > 1
        or any(len(values) > 1 for values in request_aliases)
        or any(len(service_ids) > 1 or len(version_hashes) > 1
               for service_ids, version_hashes in service_aliases)
        or any(len(_aliases(edge, "talkroom_id", "talkroomId")) > 1 for edge in edges)
        or any(request in ambiguous_requests for request in request_ids)
        or len(storefront_ids) > 1
        or (service_fields_present and len(storefront_ids) != 1)
        or (bool(request_ids) and service_fields_present)
        or len(application_ids) > 1
    )
    if conflict:
        return "unknown", _identity(talkroom_id=room), "conflicting exact acquisition edges"
    if len(request_ids) == 1 and len(application_ids) == 1:
        opportunity = next(iter(request_ids))
        return "apply", _identity(
            opportunity_id=opportunity,
            application_id=next(iter(application_ids)),
            talkroom_id=room,
        ), None
    if len(storefront_ids) == 1 and not request_ids:
        service_id, version_hash = next(iter(storefront_ids))
        return "storefront", _identity(
            service_id=service_id,
            service_version_hash=version_hash,
            talkroom_id=room,
        ), None
    if request_ids:
        reason = "request edge has no application receipt"
    elif service_fields_present:
        reason = "incomplete storefront acquisition edge"
    else:
        reason = "no exact acquisition edge"
    return "unknown", _identity(talkroom_id=room), reason


def reconcile_rows(
    earnings: Iterable[dict[str, Any]],
    identities: Iterable[dict[str, Any]],
    applications: Iterable[dict[str, Any]],
    *,
    source_sha256: str,
) -> dict[str, Any]:
    identity_rows = list(identities)
    by_room: dict[str, list[dict[str, Any]]] = {}
    request_rooms: dict[str, set[str]] = {}
    for edge in identity_rows:
        rooms = _aliases(edge, "talkroom_id", "talkroomId")
        requests = _aliases(edge, "request_id", "opportunity_id")
        for room in rooms:
            by_room.setdefault(room, []).append(edge)
            for request in requests:
                request_rooms.setdefault(request, set()).add(room)
    ambiguous_requests = {
        request for request, rooms in request_rooms.items() if len(rooms) > 1
    }
    verified_applications, application_conflicts = verified_application_identities(applications)
    ambiguous_requests.update(application_conflicts)
    totals = {lane: {"count": 0, "net_jpy": 0} for lane in (
        "storefront", "apply", "unknown", "all"
    )}
    eligible: list[tuple[dict[str, Any], str, str, int, str]] = []
    receipts: set[str] = set()
    for row in earnings:
        if row.get("status") not in SETTLED:
            continue
        evidence_value = row.get("evidence")
        if evidence_value is None or evidence_value == "":
            continue
        if not isinstance(evidence_value, str):
            raise ReconciliationError("settlement evidence must be text")
        evidence = evidence_value.strip()
        if evidence_value != evidence:
            raise ReconciliationError("settlement evidence has surrounding whitespace")
        if not evidence:
            continue
        amount = row.get("jpy")
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise ReconciliationError("settlement JPY must be numeric")
        if not math.isfinite(amount):
            raise ReconciliationError("settlement JPY must be finite")
        if amount <= 0:
            continue
        if int(amount) != amount:
            raise ReconciliationError("settlement JPY must be an integer")
        if abs(amount) > MAX_SAFE_INTEGER:
            raise ReconciliationError("settlement JPY exceeds the safe integer range")
        rooms = _aliases(row, "talkroom_id", "requestId")
        receipt_ids = _aliases(row, "idem_key", "payment_receipt_id")
        if len(rooms) > 1:
            raise ReconciliationError("talkroom aliases conflict")
        if len(receipt_ids) > 1:
            raise ReconciliationError("payment receipt aliases conflict")
        room = next(iter(rooms)) if len(rooms) == 1 else ""
        receipt = next(iter(receipt_ids)) if len(receipt_ids) == 1 else ""
        if not room or not receipt:
            raise ReconciliationError("settlement requires talkroom and payment receipt")
        if receipt in receipts:
            raise ReconciliationError("duplicate payment receipt")
        receipts.add(receipt)
        eligible.append((row, room, receipt, int(amount), evidence))
    source_net = sum(item[3] for item in eligible)
    source_receipts = {item[2] for item in eligible}
    events: list[dict[str, Any]] = []
    for row, room, receipt, amount, evidence in eligible:
        lane, identity, reason = _lane_for(
            room, by_room.get(room, []), verified_applications, ambiguous_requests
        )
        identity["payment_receipt_id"] = receipt
        occurred_at = _rfc3339(row.get("ts"))
        if "observed_at" in row:
            observed_source = row["observed_at"]
        elif "payout_state_observed_at" in row:
            observed_source = row["payout_state_observed_at"]
        else:
            observed_source = row.get("ts")
        observed_at = _rfc3339(observed_source)
        if dt.datetime.fromisoformat(observed_at) < dt.datetime.fromisoformat(occurred_at):
            raise ReconciliationError("settlement observed before occurrence")
        event = {
            "schema_version": 1,
            "record_kind": "event",
            "platform": "coconala",
            "acquisition_lane": lane,
            "observed_at": observed_at,
            "source": {
                "collector": "revenue_collector",
                "evidence_ref": evidence,
                "content_sha256": source_sha256,
            },
            "event_id": f"coconala:settlement:{receipt}",
            "event_name": "settled",
            "occurred_at": occurred_at,
            "identity": identity,
            "identity_status": "unknown" if lane == "unknown" else "known",
            "unknown_reason": reason,
            "amount": {
                "status": "known", "net_jpy": amount, "currency": "JPY",
                "unknown_reason": None,
            },
        }
        validate_kpi_record(event)
        events.append(event)
        for bucket in (lane, "all"):
            totals[bucket]["count"] += 1
            totals[bucket]["net_jpy"] += amount
    event_receipts = {event["identity"]["payment_receipt_id"] for event in events}
    event_net = sum(event["amount"]["net_jpy"] for event in events)
    conserved = (
        len(events) == len(eligible)
        and event_receipts == source_receipts
        and event_net == source_net
        and all(
        totals["all"][key] == sum(totals[lane][key] for lane in (
            "storefront", "apply", "unknown"
        )) for key in ("count", "net_jpy")
        )
    )
    if not conserved:
        raise ReconciliationError("lane totals do not conserve the source ledger")
    return {"events": events, "totals": totals, "conserved": True}


def _rows(content: bytes, name: str) -> list[dict[str, Any]]:
    def reject_constant(_value: str):
        raise ValueError("non-standard JSON constant")

    try:
        text = content.decode("utf-8")
        rows = [json.loads(line, parse_constant=reject_constant)
                for line in text.splitlines() if line.strip()]
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ReconciliationError(f"malformed {name}") from exc
    if not all(isinstance(row, dict) for row in rows):
        raise ReconciliationError(f"malformed {name}")
    return rows


def reconcile_state(state_dir: Path) -> dict[str, Any]:
    earnings_path = state_dir / "earnings.jsonl"
    identity_path = state_dir / "identity_chain.jsonl"
    applications_path = state_dir / "applied.jsonl"
    paths = (earnings_path, identity_path, applications_path)
    contents = {path: path.read_bytes() if path.exists() else b"" for path in paths}
    rows = {path: _rows(contents[path], path.name) for path in paths}
    report = reconcile_rows(
        rows[earnings_path], rows[identity_path], rows[applications_path],
        source_sha256=hashlib.sha256(contents[earnings_path]).hexdigest(),
    )
    report["inputs"] = {
        path.name: {
            "row_offset": len(rows[path]),
            "content_sha256": hashlib.sha256(contents[path]).hexdigest(),
        }
        for path in paths
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", type=Path, default=Path.home() / "gig")
    args = parser.parse_args()
    json.dump(reconcile_state(args.state_dir), sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
