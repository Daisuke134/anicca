#!/usr/bin/env python3
"""Validate and durably store public-safe Capafy revenue events."""

from __future__ import annotations

import copy
import fcntl
import argparse
import json
import os
import re
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


EVENT_TYPES = {
    "listing.submitted",
    "listing.approved",
    "content.published",
    "content.measured",
    "account.created",
    "account.session_ready",
    "account.publish_probe_ready",
    "account.post_verified",
    "order.received",
    "balance.reconciled",
    "payout.received",
    "cost.measured",
    "incident.detected",
    "incident.repair_started",
    "incident.repaired",
    "incident.verified",
    "incident.unresolved",
}
MONEY_FIELDS = (
    "gross_delta",
    "pending_delta",
    "realized_delta",
    "mrr_delta",
    "cost_delta",
    "contribution_delta",
)
METRIC_FIELDS = {"impressions", "views", "clicks", "likes", "comments", "orders"}
TOP_LEVEL_FIELDS = {
    "schema_version",
    "event_id",
    "event_type",
    "occurred_at",
    "recorded_at",
    "loop",
    "entity",
    "correlation_id",
    "summary",
    "status",
    "money",
    "metrics",
    "public_evidence",
    "technical_evidence_ref",
    "source",
    "next",
}
MONEY_PATTERN = re.compile(r"^-?(?:0|[1-9][0-9]*)\.[0-9]{2}$")
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
EVENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._-]*$")
CREDENTIAL_KEYS = {"password", "passwd", "token", "secret", "cookie", "authorization"}
PRIVATE_PATH_PREFIXES = ("/Users/", "/private/", "~/", "file:")


@dataclass(frozen=True)
class AppendResult:
    event_id: str
    appended: bool
    ledger_count: int
    evidence_path: str | None


def _walk(value: Any):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _walk_keys(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def _is_utc_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0


def _is_https_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _required_string(container: dict, field: str, errors: list[str]) -> None:
    if not isinstance(container.get(field), str) or not container[field].strip():
        errors.append(f"{field} is required")


def validate_event(event: dict) -> list[str]:
    """Return all fixed-contract violations without mutating *event*."""

    if not isinstance(event, dict):
        return ["event must be an object"]

    errors: list[str] = []
    if event.get("schema_version") != 1:
        errors.append("schema_version must be 1")

    unknown = sorted(set(event) - TOP_LEVEL_FIELDS)
    if unknown:
        errors.append(f"unsupported top-level fields: {', '.join(unknown)}")

    _required_string(event, "event_id", errors)
    if isinstance(event.get("event_id"), str) and not EVENT_ID_PATTERN.fullmatch(
        event["event_id"]
    ):
        errors.append("event_id contains unsupported characters")
    event_type = event.get("event_type")
    if event_type not in EVENT_TYPES:
        errors.append(f"unsupported event_type: {event_type!r}")
    for field in ("loop", "summary", "technical_evidence_ref"):
        _required_string(event, field, errors)

    for field in ("occurred_at", "recorded_at"):
        if not _is_utc_timestamp(event.get(field)):
            errors.append(f"{field} must be an RFC3339 UTC timestamp")

    correlation_id = event.get("correlation_id")
    if correlation_id is not None and (
        not isinstance(correlation_id, str) or not correlation_id.strip()
    ):
        errors.append("correlation_id must be a non-empty string or null")

    entity = event.get("entity")
    if not isinstance(entity, dict) or set(entity) != {"type", "id"}:
        errors.append("entity must contain exactly type and id")
    elif not all(isinstance(entity[name], str) and entity[name].strip() for name in entity):
        errors.append("entity.type and entity.id are required")

    status = event.get("status")
    if not isinstance(status, dict) or set(status) != {"before", "after"}:
        errors.append("status must contain exactly before and after")
    elif any(value is not None and not isinstance(value, str) for value in status.values()):
        errors.append("status values must be strings or null")

    money = event.get("money")
    expected_money = {"currency", *MONEY_FIELDS}
    if not isinstance(money, dict) or set(money) != expected_money:
        errors.append("money must contain currency and all six delta fields")
    else:
        if money.get("currency") != "USD":
            errors.append("money.currency must be USD")
        for field in MONEY_FIELDS:
            if not isinstance(money[field], str) or not MONEY_PATTERN.fullmatch(money[field]):
                errors.append(f"money.{field} must be a two-decimal string")

    metrics = event.get("metrics")
    if not isinstance(metrics, dict):
        errors.append("metrics must be an object")
    else:
        for field, value in metrics.items():
            if field not in METRIC_FIELDS:
                errors.append(f"unsupported metric: {field}")
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                errors.append(f"metrics.{field} must be a non-negative integer")

    public_evidence = event.get("public_evidence")
    if not isinstance(public_evidence, dict) or set(public_evidence) != {"urls", "labels"}:
        errors.append("public_evidence must contain exactly urls and labels")
    else:
        urls = public_evidence["urls"]
        labels = public_evidence["labels"]
        if not isinstance(urls, list) or not all(_is_https_url(url) for url in urls):
            errors.append("public_evidence.urls must contain only HTTPS URLs")
        if not isinstance(labels, list) or not all(
            isinstance(label, str) and label.strip() for label in labels
        ):
            errors.append("public_evidence.labels must contain only non-empty strings")

    source = event.get("source")
    if not isinstance(source, dict) or set(source) != {"producer", "source_id", "source_digest"}:
        errors.append("source must contain exactly producer, source_id, and source_digest")
    else:
        for field in ("producer", "source_id"):
            if not isinstance(source[field], str) or not source[field].strip():
                errors.append(f"source.{field} is required")
        if not isinstance(source["source_digest"], str) or not DIGEST_PATTERN.fullmatch(
            source["source_digest"]
        ):
            errors.append("source.source_digest must be sha256:<64 lowercase hex>")

    next_action = event.get("next")
    if not isinstance(next_action, dict) or set(next_action) != {"owner", "retry_at"}:
        errors.append("next must contain exactly owner and retry_at")
    else:
        if not isinstance(next_action["owner"], str) or not next_action["owner"].strip():
            errors.append("next.owner is required")
        if next_action["retry_at"] is not None and not _is_utc_timestamp(next_action["retry_at"]):
            errors.append("next.retry_at must be an RFC3339 UTC timestamp or null")

    if any(
        isinstance(value, str)
        and any(prefix in value for prefix in PRIVATE_PATH_PREFIXES)
        for value in _walk(event)
    ):
        errors.append("public event contains a private local path")

    if any(key.lower().replace("-", "_") in CREDENTIAL_KEYS for key in _walk_keys(event)):
        errors.append("public event contains a credential-bearing key")

    return errors


def canonical_event_bytes(event: dict) -> bytes:
    """Serialize one event with stable key order and no presentation whitespace."""

    return json.dumps(
        event, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def semantic_event_bytes(event: dict) -> bytes:
    """Serialize the producer-owned payload, excluding the store receipt timestamp."""

    semantic = dict(event)
    semantic.pop("recorded_at", None)
    return canonical_event_bytes(semantic)


def _read_events_unlocked(ledger: Path) -> list[dict]:
    if not ledger.exists():
        return []
    events: list[dict] = []
    with ledger.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid ledger JSON at line {line_number}: {exc.msg}") from exc
            errors = validate_event(event)
            if errors:
                raise ValueError(
                    f"invalid ledger event at line {line_number}: {'; '.join(errors)}"
                )
            events.append(event)
    return events


def read_events(ledger: Path) -> list[dict]:
    """Read and validate every non-empty event row."""

    return _read_events_unlocked(Path(ledger))


def _write_sidecar(evidence_dir: Path, event_id: str, evidence: dict) -> Path:
    evidence_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(evidence_dir, 0o700)
    destination = evidence_dir / f"{event_id}.json"
    content = canonical_event_bytes(evidence) + b"\n"
    if destination.exists():
        if destination.read_bytes() != content:
            raise ValueError(f"technical evidence conflict for event_id: {event_id}")
        os.chmod(destination, 0o600)
        return destination

    descriptor, temporary_name = tempfile.mkstemp(prefix=".capafy-evidence-", dir=evidence_dir)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        os.chmod(destination, 0o600)
    finally:
        if temporary.exists():
            temporary.unlink()
    return destination


def append_event(
    ledger: Path,
    event: dict,
    evidence: dict | None,
    evidence_dir: Path,
) -> AppendResult:
    """Append a new semantic event once, or return a successful duplicate receipt."""

    ledger = Path(ledger)
    evidence_dir = Path(evidence_dir)
    prepared = copy.deepcopy(event)
    prepared["recorded_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )
    errors = validate_event(prepared)
    if errors:
        raise ValueError("invalid event: " + "; ".join(errors))

    ledger.parent.mkdir(parents=True, exist_ok=True)
    lock_path = ledger.with_suffix(".lock")
    lock_descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        os.chmod(lock_path, 0o600)
        fcntl.flock(lock_descriptor, fcntl.LOCK_EX)
        existing = _read_events_unlocked(ledger)
        for prior in existing:
            if prior["event_id"] != prepared["event_id"]:
                continue
            if semantic_event_bytes(prior) != semantic_event_bytes(prepared):
                raise ValueError(f"event_id conflict: {prepared['event_id']}")
            evidence_path = None
            if evidence is not None:
                evidence_path = str(
                    _write_sidecar(evidence_dir, prepared["event_id"], evidence)
                )
            return AppendResult(prepared["event_id"], False, len(existing), evidence_path)

        evidence_path = None
        if evidence is not None:
            evidence_path = str(_write_sidecar(evidence_dir, prepared["event_id"], evidence))

        descriptor = os.open(ledger, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "ab") as handle:
            handle.write(canonical_event_bytes(prepared) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        return AppendResult(prepared["event_id"], True, len(existing) + 1, evidence_path)
    finally:
        fcntl.flock(lock_descriptor, fcntl.LOCK_UN)
        os.close(lock_descriptor)


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate", help="validate one persisted event from stdin")
    append_parser = commands.add_parser("append", help="append one event from stdin")
    append_parser.add_argument("--ledger", type=Path, required=True)
    append_parser.add_argument("--evidence-dir", type=Path, required=True)
    read_parser = commands.add_parser("read", help="read all validated public events")
    read_parser.add_argument("--ledger", type=Path, required=True)
    args = parser.parse_args()

    try:
        if args.command == "read":
            output = {"events": read_events(args.ledger)}
        else:
            event = json.load(sys.stdin)
            if args.command == "validate":
                errors = validate_event(event)
                if errors:
                    raise ValueError("; ".join(errors))
                output = {"valid": True}
            else:
                evidence_text = os.environ.get("CAPAFY_EVENT_EVIDENCE_JSON")
                evidence = json.loads(evidence_text) if evidence_text else None
                if evidence is not None and not isinstance(evidence, dict):
                    raise ValueError("CAPAFY_EVENT_EVIDENCE_JSON must be a JSON object")
                output = asdict(
                    append_event(args.ledger, event, evidence, args.evidence_dir)
                )
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(json.dumps(output, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
