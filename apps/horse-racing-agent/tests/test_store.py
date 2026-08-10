import copy
import json
import math
from pathlib import Path

import pytest

from horse_racing_agent.store import (
    AppendOnlyStore,
    StoreRecordRejected,
    StoredRecord,
    canonical_content_hash,
    validate_normalized_race,
)


# Test-only mechanics fixture. Values are opaque normalized examples, not evidence
# and deliberately contain no horse, person, or raw source-row values.
FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures/normalized_races.json").read_text()
)
NAR = FIXTURES["nar_official"]
JRA = FIXTURES["jra_official"]
JRA_OFFICIAL_URL = "https://www.jra.go.jp/JRADB/accessS.html?CNAME=pw01sde1004202602060720260809/DD"
NAR_OFFICIAL_URL = "https://www.keiba.go.jp/KeibaWeb/DataDownload/RaceDataDownload?type=daily"


def _secondary_record() -> dict[str, object]:
    record = copy.deepcopy(JRA)
    record.update(
        {
            "record_id": "record-jra-secondary-001",
            "event_id": "event-jra-secondary-001",
            "race_id": "race-jra-secondary-001",
            "source_url": "https://race.netkeiba.com/opaque/race-result",
            "source_authority": "secondary",
            "evidence_class": "PUBLIC_WEB_SECONDARY",
            "allowed_scope": "shadow_only",
        }
    )
    return record


def _official_scope_contract_record(record: dict[str, object]) -> dict[str, object]:
    """Make an ephemeral source-scope case; this is not observed evidence."""
    official = copy.deepcopy(record)
    official.update(
        {
            "evidence_class": "REAL_PUBLIC_WEB_RECORD",
            "allowed_scope": "private_shadow",
        }
    )
    return official


def _copy_with(record: dict[str, object], **changes: object) -> dict[str, object]:
    updated = copy.deepcopy(record)
    updated.update(changes)
    return updated


def test_committed_fixture_is_synthetic_test_only_with_exact_official_urls():
    assert set(FIXTURES) == {"nar_official", "jra_official"}
    assert NAR["evidence_class"] == JRA["evidence_class"] == "SYNTHETIC_TEST"
    assert NAR["allowed_scope"] == JRA["allowed_scope"] == "test_only"
    assert NAR["source_url"] == NAR_OFFICIAL_URL
    assert JRA["source_url"] == JRA_OFFICIAL_URL
    assert NAR["surface"] is None and NAR["track_condition"] is None
    assert JRA["surface"] is None and JRA["track_condition"] is None
    for example in FIXTURES.values():
        for runner in example["runners"]:
            assert runner["odds"] is None
            assert runner["body_weight_kg"] is None
            assert "horse_name" not in runner


def test_official_source_scope_contract_accepts_ephemeral_cases_not_evidence():
    nar = _official_scope_contract_record(NAR)
    jra = _official_scope_contract_record(JRA)
    assert validate_normalized_race(nar)["jurisdiction"] == "NAR"
    assert validate_normalized_race(jra)["jurisdiction"] == "JRA"
    assert nar["allowed_scope"] == jra["allowed_scope"] == "private_shadow"


def test_secondary_source_scope_contract_accepts_ephemeral_case_not_evidence():
    # Ephemeral scope-contract case only; this fixture is not secondary evidence.
    record = validate_normalized_race(_secondary_record())
    assert record["source_authority"] == "secondary"
    assert record["evidence_class"] == "PUBLIC_WEB_SECONDARY"
    assert record["allowed_scope"] == "shadow_only"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_authority", "secondary"),
        ("jurisdiction", "NAR"),
        ("allowed_scope", "shadow_only"),
    ],
)
def test_rejects_source_jurisdiction_or_scope_mismatch(field, value):
    with pytest.raises(StoreRecordRejected):
        validate_normalized_race(_copy_with(JRA, **{field: value}))


def test_rejects_raw_value_export():
    with pytest.raises(StoreRecordRejected, match="raw values"):
        validate_normalized_race(_copy_with(NAR, raw_values_exported=True))


@pytest.mark.parametrize("field", ["odds", "body_weight_kg"])
@pytest.mark.parametrize("invalid", [0, math.nan, math.inf, -math.inf])
def test_rejects_zero_or_nonfinite_unobserved_numeric_values(field, invalid):
    record = _copy_with(NAR)
    record["runners"][0][field] = invalid
    with pytest.raises(StoreRecordRejected):
        validate_normalized_race(record)


@pytest.mark.parametrize("field", ["surface", "track_condition"])
@pytest.mark.parametrize("invalid", [0, ""])
def test_rejects_zero_or_empty_unobserved_track_values(field, invalid):
    with pytest.raises(StoreRecordRejected):
        validate_normalized_race(_copy_with(NAR, **{field: invalid}))


@pytest.mark.parametrize(
    "changes",
    [
        {"record_id": ""},
        {"event_id": ""},
        {"race_id": ""},
        {"runners": [{"runner_id": "opaque", "horse_number": 1, "odds": 2.0}]},
        {"snapshot_at": "2026-08-09T10:54:00"},
    ],
)
def test_rejects_exact_field_and_timestamp_contract_violations(changes):
    with pytest.raises(StoreRecordRejected):
        validate_normalized_race(_copy_with(NAR, **changes))


def test_hash_is_deterministic_and_excludes_storage_ids():
    reordered = {key: NAR[key] for key in reversed(NAR)}
    assert canonical_content_hash(NAR) == canonical_content_hash(reordered)
    assert canonical_content_hash(NAR) == canonical_content_hash(
        _copy_with(NAR, record_id="other-record", event_id="other-event")
    )


def test_append_returns_redacted_stored_record_without_runners():
    store = AppendOnlyStore()
    stored = store.append(copy.deepcopy(NAR))
    assert isinstance(stored, StoredRecord)
    assert stored.record_id == NAR["record_id"]
    assert stored.event_id == NAR["event_id"]
    assert stored.source_url == NAR["source_url"]
    assert stored.jurisdiction == "NAR"
    assert not hasattr(stored, "runners")
    assert not hasattr(stored, "raw_payload")


def test_append_rejects_duplicate_ids_and_source_hash_identity():
    store = AppendOnlyStore()
    store.append(copy.deepcopy(NAR))
    with pytest.raises(StoreRecordRejected, match="record id"):
        store.append(_copy_with(NAR, event_id="event-nar-other"))
    with pytest.raises(StoreRecordRejected, match="event id"):
        store.append(_copy_with(NAR, record_id="record-nar-other"))

    changed_ids_same_content = _copy_with(
        NAR, record_id="record-nar-third", event_id="event-nar-third"
    )
    with pytest.raises(StoreRecordRejected, match="source/hash"):
        store.append(changed_ids_same_content)


def test_append_and_get_isolate_caller_and_return_aliases():
    store = AppendOnlyStore()
    caller_record = copy.deepcopy(NAR)
    store.append(caller_record)
    caller_record["runners"][0]["odds"] = 999.0
    assert store._records[NAR["record_id"]]["record"]["runners"][0]["odds"] is None

    returned = store.get(NAR["record_id"])
    assert returned == store.get(NAR["record_id"])
    with pytest.raises((AttributeError, TypeError)):
        returned.record_id = "mutated"


def test_rejects_stale_or_equal_snapshot_for_same_jurisdiction_and_race():
    store = AppendOnlyStore()
    store.append(copy.deepcopy(NAR))
    later = _copy_with(
        NAR,
        record_id="record-nar-later",
        event_id="event-nar-later",
        snapshot_at="2026-08-09T10:56:00+09:00",
        cutoff_at="2026-08-09T10:57:00+09:00",
    )
    store.append(later)
    stale = _copy_with(
        later,
        record_id="record-nar-stale",
        event_id="event-nar-stale",
        snapshot_at="2026-08-09T10:55:00+09:00",
    )
    equal = _copy_with(
        later,
        record_id="record-nar-equal",
        event_id="event-nar-equal",
        runners=[
            {"runner_id": "runner-opaque-01", "horse_number": 1, "odds": 2.6, "body_weight_kg": 480.0},
            {"runner_id": "runner-opaque-02", "horse_number": 2, "odds": 4.0, "body_weight_kg": 470.0},
        ],
    )
    with pytest.raises(StoreRecordRejected, match="snapshot"):
        store.append(stale)
    with pytest.raises(StoreRecordRejected, match="snapshot"):
        store.append(equal)
