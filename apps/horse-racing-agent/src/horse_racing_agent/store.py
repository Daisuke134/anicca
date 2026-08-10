from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import math
from typing import Any

from horse_racing_agent.ingest import _source_scope


_FIELDS = {
    "schema_version",
    "record_id",
    "event_id",
    "race_id",
    "source_url",
    "source_authority",
    "jurisdiction",
    "evidence_class",
    "allowed_scope",
    "permission_document_verified",
    "raw_values_exported",
    "race_at",
    "snapshot_at",
    "cutoff_at",
    "freshness",
    "surface",
    "track_condition",
    "runners",
}
_RUNNER_FIELDS = {"runner_id", "horse_number", "odds", "body_weight_kg"}
_EVIDENCE_CLASSES = {
    "SYNTHETIC_TEST",
    "REAL_PUBLIC_WEB_RECORD",
    "PUBLIC_WEB_SECONDARY",
}


class StoreRecordRejected(ValueError):
    """Raised when a normalized record cannot enter the append-only store."""


@dataclass(frozen=True)
class StoredRecord:
    """Redacted metadata returned by the append-only store.

    Runner values and raw payloads are intentionally absent. The normalized
    record remains private to the in-memory store for snapshot validation.
    """

    record_id: str
    event_id: str
    source_url: str
    content_sha256: str
    jurisdiction: str | None = None
    race_id: str | None = None


def _reject(message: str) -> None:
    raise StoreRecordRejected(message)


def _require(condition: bool, message: str) -> None:
    if not condition:
        _reject(message)


def _opaque_id(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _parse_timestamp(value: object) -> datetime:
    _require(isinstance(value, str), "normalized timestamps are invalid")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        _reject("normalized timestamps are invalid")
    _require(
        parsed.tzinfo is not None and parsed.utcoffset() is not None,
        "normalized timestamps are invalid",
    )
    return parsed


def _validate_source_scope(record: dict[str, object]) -> str:
    try:
        scope = _source_scope(
            record["source_url"],
            record["source_authority"],
            record["jurisdiction"],
        )
    except (KeyError, TypeError, ValueError):
        _reject("source/jurisdiction mapping is invalid")

    evidence_class = record["evidence_class"]
    allowed_scope = record["allowed_scope"]
    if evidence_class == "REAL_PUBLIC_WEB_RECORD":
        expected_scope = "private_shadow"
    elif evidence_class == "PUBLIC_WEB_SECONDARY":
        expected_scope = "shadow_only"
    elif evidence_class == "SYNTHETIC_TEST":
        # Synthetic mechanics use an accepted source tuple but cannot inherit
        # its public-web scope. They are explicitly test-only.
        expected_scope = "test_only"
    else:
        _reject("evidence class is invalid")

    _require(allowed_scope == expected_scope, "source/evidence scope is invalid")
    if evidence_class != "SYNTHETIC_TEST":
        _require(scope == expected_scope, "source/evidence scope is invalid")
    return scope


def validate_normalized_race(record: dict[str, object]) -> dict[str, object]:
    """Validate and deep-copy one observed, normalized race record."""

    _require(isinstance(record, dict), "normalized race schema is invalid")
    _require(set(record) == _FIELDS, "normalized race schema is invalid")
    _require(
        type(record["schema_version"]) is int and record["schema_version"] == 1,
        "normalized race schema is invalid",
    )

    for field in ("record_id", "event_id", "race_id"):
        _require(_opaque_id(record[field]), "normalized race identity is invalid")

    for field in (
        "source_url",
        "source_authority",
        "jurisdiction",
        "evidence_class",
        "allowed_scope",
    ):
        _require(
            isinstance(record[field], str) and bool(record[field].strip()),
            "normalized source fields are invalid",
        )
    _require(record["evidence_class"] in _EVIDENCE_CLASSES, "evidence class is invalid")
    _validate_source_scope(record)

    _require(
        type(record["permission_document_verified"]) is bool,
        "permission metadata is invalid",
    )
    _require(record["raw_values_exported"] is False, "raw values must not be exported")

    race_at = _parse_timestamp(record["race_at"])
    snapshot_at = _parse_timestamp(record["snapshot_at"])
    cutoff_at = _parse_timestamp(record["cutoff_at"])
    _require(snapshot_at <= cutoff_at <= race_at, "normalized timestamp order is invalid")

    freshness = record["freshness"]
    _require(
        isinstance(freshness, dict) and set(freshness) == {"status", "age_seconds"},
        "freshness is invalid",
    )
    _require(freshness["status"] in {"fresh", "stale"}, "freshness is invalid")
    _require(
        _finite_number(freshness["age_seconds"]) and freshness["age_seconds"] >= 0,
        "freshness is invalid",
    )

    _require(
        isinstance(record["surface"], str)
        and bool(record["surface"].strip())
        and isinstance(record["track_condition"], str)
        and bool(record["track_condition"].strip()),
        "track fields are invalid",
    )

    runners = record["runners"]
    _require(isinstance(runners, list) and bool(runners), "runners are invalid")
    for runner in runners:
        _require(
            isinstance(runner, dict) and set(runner) == _RUNNER_FIELDS,
            "runner schema is invalid",
        )
        _require(_opaque_id(runner["runner_id"]), "runner identity is invalid")
        _require(
            type(runner["horse_number"]) is int and runner["horse_number"] > 0,
            "runner number is invalid",
        )
        _require(
            _finite_number(runner["odds"]) and runner["odds"] > 0,
            "runner odds are invalid",
        )
        _require(
            _finite_number(runner["body_weight_kg"]) and runner["body_weight_kg"] > 0,
            "runner weight is invalid",
        )

    return deepcopy(record)


def canonical_content_hash(record: dict[str, object]) -> str:
    """Hash normalized content, excluding storage-assigned semantic IDs."""

    normalized = validate_normalized_race(record)
    normalized.pop("record_id")
    normalized.pop("event_id")
    canonical = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class AppendOnlyStore:
    """Small in-memory append-only store for redacted observed metadata."""

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}
        self._events: set[str] = set()
        self._source_hashes: set[tuple[str, str]] = set()
        self._latest_snapshots: dict[tuple[str, str], datetime] = {}

    def append(self, record: dict[str, object]) -> StoredRecord:
        normalized = validate_normalized_race(record)
        record_id = normalized["record_id"]
        event_id = normalized["event_id"]
        source_url = normalized["source_url"]
        race_key = (normalized["jurisdiction"], normalized["race_id"])
        content_sha256 = canonical_content_hash(normalized)
        source_hash_key = (source_url, content_sha256)

        _require(record_id not in self._records, "duplicate record id")
        _require(event_id not in self._events, "duplicate event id")
        _require(source_hash_key not in self._source_hashes, "duplicate source/hash identity")

        snapshot_at = _parse_timestamp(normalized["snapshot_at"])
        latest_snapshot = self._latest_snapshots.get(race_key)
        _require(
            latest_snapshot is None or snapshot_at > latest_snapshot,
            "snapshot must be strictly later",
        )

        stored = StoredRecord(
            record_id=record_id,
            event_id=event_id,
            source_url=source_url,
            content_sha256=content_sha256,
            jurisdiction=normalized["jurisdiction"],
            race_id=normalized["race_id"],
        )
        self._records[record_id] = {"stored": stored, "record": deepcopy(normalized)}
        self._events.add(event_id)
        self._source_hashes.add(source_hash_key)
        self._latest_snapshots[race_key] = snapshot_at
        return deepcopy(stored)

    def get(self, record_id: str) -> StoredRecord:
        _require(record_id in self._records, "record id is not present")
        return deepcopy(self._records[record_id]["stored"])
