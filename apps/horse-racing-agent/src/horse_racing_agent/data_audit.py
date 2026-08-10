from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from types import MappingProxyType
from typing import Mapping as TypingMapping

from horse_racing_agent.ingest import _source_scope
from horse_racing_agent.store import (
    StoreRecordRejected,
    canonical_content_hash,
    validate_normalized_race,
)


_MANIFEST_FIELDS = {
    "source_authority",
    "jurisdiction",
    "evidence_class",
    "allowed_scope",
    "parsed_row_count",
    "content_sha256",
    "settled_payback_rows",
    "settled_race_ids",
    "cash_authorized",
}
_EVIDENCE_CLASSES = {
    "SYNTHETIC_TEST",
    "REAL_PUBLIC_WEB_RECORD",
    "PUBLIC_WEB_SECONDARY",
}
_SHA256 = re.compile(r"[0-9a-fA-F]{64}\Z")


class AuditRejected(ValueError):
    """Raised when stored records or source manifests fail the audit gate."""


@dataclass(frozen=True)
class AuditReport:
    """Redacted, immutable summary of an accepted coverage audit.

    The report deliberately contains no normalized record or runner values.
    ``missingness`` is wrapped in a read-only mapping at construction time;
    all other collections are tuples for deterministic, immutable output.
    """

    coverage_start: str | None
    coverage_end: str | None
    record_count: int
    race_count: int
    duplicate_count: int
    missingness: TypingMapping[str, int]
    timestamp_ordered: bool
    cutoff_violations: int
    max_odds_snapshot_age_seconds: float | int | None
    settled_payback_rows: int
    content_hashes: tuple[str, ...]
    evidence_classes: tuple[str, ...]
    allowed_scopes: tuple[str, ...]
    cash_authorized: bool
    model_ready: bool
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "missingness", MappingProxyType(dict(self.missingness)))
        object.__setattr__(self, "content_hashes", tuple(self.content_hashes))
        object.__setattr__(self, "evidence_classes", tuple(self.evidence_classes))
        object.__setattr__(self, "allowed_scopes", tuple(self.allowed_scopes))
        object.__setattr__(self, "blockers", tuple(self.blockers))


def _reject(message: str) -> None:
    raise AuditRejected(message)


def _timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        _reject("timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        _reject("timestamp is invalid")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _reject("timestamp is invalid")
    return parsed


def _manifest_scope(
    source_url: str,
    source_authority: str,
    jurisdiction: str,
    evidence_class: str,
    allowed_scope: str,
) -> None:
    if evidence_class == "REAL_PUBLIC_WEB_RECORD":
        expected_scope = "private_shadow"
    elif evidence_class == "PUBLIC_WEB_SECONDARY":
        expected_scope = "shadow_only"
    elif evidence_class == "SYNTHETIC_TEST":
        expected_scope = "test_only"
    else:
        _reject("manifest evidence class is invalid")
    if allowed_scope != expected_scope:
        _reject("manifest source/evidence scope is invalid")
    if evidence_class != "SYNTHETIC_TEST":
        try:
            source_scope = _source_scope(source_url, source_authority, jurisdiction)
        except (TypeError, ValueError):
            _reject("manifest source/evidence scope is invalid")
        if source_scope != expected_scope:
            _reject("manifest source/evidence scope is invalid")


def _validate_manifests(
    manifests: TypingMapping[str, object],
) -> dict[str, dict[str, object]]:
    if not isinstance(manifests, TypingMapping):
        _reject("manifests must be a mapping")
    if not manifests:
        _reject("at least one manifest is required")
    normalized: dict[str, dict[str, object]] = {}
    for source_url, manifest in manifests.items():
        if not isinstance(source_url, str) or not source_url.strip():
            _reject("manifest source URL is invalid")
        if not isinstance(manifest, TypingMapping) or set(manifest) != _MANIFEST_FIELDS:
            _reject("manifest schema is invalid")
        values = dict(manifest)
        for field in ("source_authority", "jurisdiction", "evidence_class", "allowed_scope"):
            if not isinstance(values[field], str) or not values[field].strip():
                _reject("manifest source fields are invalid")
        if not isinstance(values["parsed_row_count"], int) or isinstance(
            values["parsed_row_count"], bool
        ) or values["parsed_row_count"] < 0:
            _reject("manifest row count is invalid")
        if not isinstance(values["settled_payback_rows"], int) or isinstance(
            values["settled_payback_rows"], bool
        ) or values["settled_payback_rows"] < 0:
            _reject("manifest settled-payback count is invalid")
        settled_race_ids = values["settled_race_ids"]
        if not isinstance(settled_race_ids, (list, tuple)):
            _reject("manifest settled race IDs are invalid")
        if any(
            not isinstance(race_id, str) or not race_id.strip()
            for race_id in settled_race_ids
        ):
            _reject("manifest settled race IDs are invalid")
        if len(set(settled_race_ids)) != len(settled_race_ids):
            _reject("manifest settled race IDs are duplicate")
        if len(settled_race_ids) > values["settled_payback_rows"]:
            _reject("manifest settled race IDs exceed settled-payback count")
        values["settled_race_ids"] = tuple(settled_race_ids)
        if not isinstance(values["content_sha256"], str) or not _SHA256.fullmatch(
            values["content_sha256"]
        ):
            _reject("manifest content hash is invalid")
        if type(values["cash_authorized"]) is not bool:
            _reject("manifest cash authorization is invalid")
        if values["cash_authorized"]:
            _reject("cash authorization is not permitted by this audit")
        _manifest_scope(
            source_url,
            values["source_authority"],
            values["jurisdiction"],
            values["evidence_class"],
            values["allowed_scope"],
        )
        values["content_sha256"] = values["content_sha256"].casefold()
        normalized[source_url] = values
    return normalized


def audit_records(
    records: list[dict[str, object]] | tuple[dict[str, object], ...],
    manifests: TypingMapping[str, object],
) -> AuditReport:
    """Audit accepted normalized records against exact source manifests."""

    if not isinstance(records, (list, tuple)):
        _reject("records must be a sequence")
    manifest_map = _validate_manifests(manifests)

    normalized_records: list[dict[str, object]] = []
    record_entries: list[tuple[dict[str, object], dict[str, object], datetime]] = []
    seen_snapshots: set[tuple[str, str, datetime]] = set()
    previous_snapshot: datetime | None = None
    for record in records:
        try:
            normalized = validate_normalized_race(record)
        except (StoreRecordRejected, TypeError, KeyError) as exc:
            raise AuditRejected(str(exc)) from exc
        source_url = normalized["source_url"]
        manifest = manifest_map.get(source_url)
        if manifest is None:
            _reject("matching manifest is required")
        for field in ("source_authority", "jurisdiction", "evidence_class", "allowed_scope"):
            if normalized[field] != manifest[field]:
                _reject("record and manifest source metadata do not match")
        try:
            # Validate a deterministic, redacted content identity.  The
            # manifest hash is retained separately because it identifies the
            # captured source payload, not the normalized record.
            canonical_content_hash(normalized)
            snapshot_at = _timestamp(normalized["snapshot_at"])
            cutoff_at = _timestamp(normalized["cutoff_at"])
            race_at = _timestamp(normalized["race_at"])
        except (StoreRecordRejected, TypeError, KeyError) as exc:
            raise AuditRejected(str(exc)) from exc
        if snapshot_at > cutoff_at or cutoff_at > race_at:
            _reject("timestamp cutoff violation")
        if previous_snapshot is not None and snapshot_at < previous_snapshot:
            _reject("records must be ordered by snapshot_at")
        previous_snapshot = snapshot_at
        semantic_snapshot = (normalized["jurisdiction"], normalized["race_id"], snapshot_at)
        if semantic_snapshot in seen_snapshots:
            _reject("duplicate semantic snapshot")
        seen_snapshots.add(semantic_snapshot)
        normalized_records.append(normalized)
        record_entries.append((normalized, manifest, snapshot_at))

    missingness = {
        "surface": 0,
        "track_condition": 0,
        "odds": 0,
        "body_weight_kg": 0,
    }
    race_keys: set[tuple[str, str]] = set()
    race_times: list[datetime] = []
    official_entries: list[tuple[dict[str, object], dict[str, object], datetime]] = []
    odds_ages: list[float | int] = []
    for record, manifest, snapshot_at in record_entries:
        race_keys.add((record["jurisdiction"], record["race_id"]))
        race_times.append(_timestamp(record["race_at"]))
        missingness["surface"] += int(record["surface"] is None)
        missingness["track_condition"] += int(record["track_condition"] is None)
        for runner in record["runners"]:
            missingness["odds"] += int(runner["odds"] is None)
            missingness["body_weight_kg"] += int(runner["body_weight_kg"] is None)
        if (
            record["evidence_class"] == "REAL_PUBLIC_WEB_RECORD"
            and record["source_authority"] == "official"
            and manifest["evidence_class"] == "REAL_PUBLIC_WEB_RECORD"
            and manifest["source_authority"] == "official"
        ):
            official_entries.append((record, manifest, snapshot_at))

    latest_official: dict[tuple[str, str], tuple[dict[str, object], dict[str, object], datetime]] = {}
    for entry in official_entries:
        key = (entry[0]["jurisdiction"], entry[0]["race_id"])
        current = latest_official.get(key)
        if current is None or entry[2] > current[2]:
            latest_official[key] = entry

    official_odds_observed = False
    official_stale = False
    official_zero_rows = False
    unmatched_settlement = False
    official_race_times: set[datetime] = set()
    for record, manifest, _snapshot_at in latest_official.values():
        official_race_times.add(_timestamp(record["race_at"]))
        if record["freshness"]["status"] != "fresh":
            official_stale = True
        if manifest["parsed_row_count"] <= 0:
            official_zero_rows = True
        if record["race_id"] not in manifest["settled_race_ids"]:
            unmatched_settlement = True
        record_has_odds = any(runner["odds"] is not None for runner in record["runners"])
        if record_has_odds:
            official_odds_observed = True
            odds_ages.append(record["freshness"]["age_seconds"])

    settled_payback_rows = sum(
        int(manifest["settled_payback_rows"])
        for manifest in manifest_map.values()
        if manifest["evidence_class"] == "REAL_PUBLIC_WEB_RECORD"
        and manifest["source_authority"] == "official"
    )
    blockers: list[str] = []
    if not normalized_records:
        blockers.append("NO_NORMALIZED_ACTUAL_RECORDS")
    if settled_payback_rows == 0:
        blockers.append("NO_SETTLED_PAYBACK")
    if not official_odds_observed:
        blockers.append("NO_OBSERVED_ODDS")
    if len(latest_official) < 2 or len(official_race_times) < 2:
        blockers.append("INSUFFICIENT_CHRONOLOGY")
    if official_stale:
        blockers.append("STALE_OFFICIAL_RECORD")
    if official_zero_rows:
        blockers.append("NO_PARSED_OFFICIAL_ROWS")
    if settled_payback_rows > 0 and (not latest_official or unmatched_settlement):
        blockers.append("NO_MATCHING_SETTLED_PAYBACK")

    model_ready = bool(
        len(latest_official) >= 2
        and len(official_race_times) >= 2
        and official_odds_observed
        and settled_payback_rows > 0
        and not official_stale
        and not official_zero_rows
        and not unmatched_settlement
        and not blockers
    )
    return AuditReport(
        coverage_start=min(race_times).isoformat() if race_times else None,
        coverage_end=max(race_times).isoformat() if race_times else None,
        record_count=len(normalized_records),
        race_count=len(race_keys),
        duplicate_count=0,
        missingness=missingness,
        timestamp_ordered=True,
        cutoff_violations=0,
        max_odds_snapshot_age_seconds=max(odds_ages) if odds_ages else None,
        settled_payback_rows=settled_payback_rows,
        content_hashes=tuple(sorted({manifest["content_sha256"] for manifest in manifest_map.values()})),
        evidence_classes=tuple(sorted({manifest["evidence_class"] for manifest in manifest_map.values()})),
        allowed_scopes=tuple(sorted({manifest["allowed_scope"] for manifest in manifest_map.values()})),
        cash_authorized=False,
        model_ready=model_ready,
        blockers=tuple(sorted(blockers)),
    )
