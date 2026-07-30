#!/usr/bin/env python3
"""CloudEvents-shaped, evidence-bound unit-economics event ledger."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


EVENT_TYPES = {
    "revenue": "ai.anicca.unit_economics.revenue.settled.v1",
    "cost": "ai.anicca.unit_economics.cost.actual_billed.v1",
}
CURRENCY_EXPONENTS = {
    "JPY": 0,
    "KRW": 0,
    "VND": 0,
    "USD": 2,
    "EUR": 2,
    "GBP": 2,
    "AUD": 2,
    "CAD": 2,
    "NZD": 2,
    "CHF": 2,
    "SGD": 2,
    "HKD": 2,
    "CNY": 2,
    "INR": 2,
    "BRL": 2,
    "MXN": 2,
    "BHD": 3,
    "IQD": 3,
    "JOD": 3,
    "KWD": 3,
    "LYD": 3,
    "OMR": 3,
    "TND": 3,
    "CLF": 4,
    "UYW": 4,
}


def _occurred_at(value: Any) -> str:
    try:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            parsed = datetime.fromtimestamp(float(value), tz=timezone.utc)
        else:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError
        return parsed.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("occurred_at_invalid") from exc


def make_event(
    *,
    kind: str,
    loop: str,
    source: str,
    source_record_id: str,
    occurred_at: Any,
    amount_minor: int,
    currency: str,
    evidence: str,
    invoice_id: str | None = None,
    allocation_basis: str | None = None,
    allocation_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event_type = EVENT_TYPES.get(kind)
    if event_type is None:
        raise ValueError("event_kind_invalid")
    if not isinstance(loop, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", loop):
        raise ValueError("loop_invalid")
    if not isinstance(source, str) or not urlsplit(source).scheme:
        raise ValueError("source_must_be_absolute_uri")
    if not isinstance(source_record_id, str) or not source_record_id.strip():
        raise ValueError("source_record_id_required")
    if not isinstance(amount_minor, int) or isinstance(amount_minor, bool) or amount_minor <= 0:
        raise ValueError("amount_minor_must_be_positive_integer")
    if currency not in CURRENCY_EXPONENTS:
        raise ValueError("currency_unsupported")
    if not isinstance(evidence, str) or not evidence.strip():
        raise ValueError("evidence_required")
    if kind == "cost":
        if not isinstance(invoice_id, str) or not invoice_id.strip():
            raise ValueError("invoice_id_required")
        if not isinstance(allocation_basis, str) or not allocation_basis.strip():
            raise ValueError("allocation_basis_required")
        if allocation_metadata is not None:
            if not isinstance(allocation_metadata, dict):
                raise ValueError("allocation_metadata_invalid")
            required_strings = ("provider", "period_start", "period_end", "usage_event_ids_sha256")
            for key in required_strings:
                if not isinstance(allocation_metadata.get(key), str) or not allocation_metadata[key].strip():
                    raise ValueError(f"allocation_metadata_{key}_invalid")
            if not re.fullmatch(r"[0-9a-f]{64}", allocation_metadata["usage_event_ids_sha256"]):
                raise ValueError("allocation_metadata_usage_event_ids_sha256_invalid")
            for key in ("usage_event_count", "allocated_tokens", "invoice_total_tokens"):
                metric = allocation_metadata.get(key)
                if not isinstance(metric, int) or isinstance(metric, bool) or metric <= 0:
                    raise ValueError(f"allocation_metadata_{key}_invalid")

    event_id = hashlib.sha256(
        f"{source}\0{source_record_id}\0{event_type}".encode("utf-8")
    ).hexdigest()
    data: dict[str, Any] = {
        "loop": loop,
        "recognition": "settled" if kind == "revenue" else "actual_billed",
        "amount_minor": amount_minor,
        "currency": currency,
        "minor_unit_exponent": CURRENCY_EXPONENTS[currency],
        "evidence": evidence.strip(),
    }
    if kind == "cost":
        data.update(
            {
                "invoice_id": invoice_id.strip(),
                "allocation_basis": allocation_basis.strip(),
            }
        )
        if allocation_metadata:
            data.update(allocation_metadata)
    return {
        "specversion": "1.0",
        "id": event_id,
        "source": source,
        "type": event_type,
        "time": _occurred_at(occurred_at),
        "datacontenttype": "application/json",
        "data": data,
    }


def _validate_event(event: dict[str, Any]) -> None:
    if not isinstance(event, dict):
        raise ValueError("event_not_object")
    if event.get("specversion") != "1.0":
        raise ValueError("event_specversion_invalid")
    if not re.fullmatch(r"[0-9a-f]{64}", str(event.get("id") or "")):
        raise ValueError("event_id_invalid")
    if not isinstance(event.get("source"), str) or not urlsplit(event["source"]).scheme:
        raise ValueError("event_source_invalid")
    if event.get("type") not in EVENT_TYPES.values():
        raise ValueError("event_type_invalid")
    if not isinstance(event.get("data"), dict):
        raise ValueError("event_data_invalid")
    _occurred_at(event.get("time"))


def append_event(ledger: str | Path, event: dict[str, Any]) -> bool:
    """Append once by CloudEvents ``source`` + ``id`` under an owner-only lock."""
    _validate_event(event)
    target = Path(ledger).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.parent.chmod(0o700)
    lock_path = target.with_name(f".{target.name}.lock")
    lock_fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        os.chmod(lock_path, 0o600)
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        existing_keys: set[tuple[str, str]] = set()
        if target.exists():
            with target.open(encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise ValueError("economics_ledger_contains_invalid_json") from exc
                    if not isinstance(row, dict):
                        raise ValueError("economics_ledger_contains_non_object")
                    existing_keys.add((str(row.get("source") or ""), str(row.get("id") or "")))
        key = (event["source"], event["id"])
        if key in existing_keys:
            return False
        payload = (
            json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode()
        ledger_fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.chmod(target, 0o600)
            written = os.write(ledger_fd, payload)
            if written != len(payload):
                raise OSError("short economics ledger append")
            os.fsync(ledger_fd)
        finally:
            os.close(ledger_fd)
        return True
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)
