from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from horse_racing_agent.data_audit import AuditRejected, AuditReport, audit_records


FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures/normalized_races.json").read_text()
)
NAR = FIXTURES["nar_official"]
JRA = FIXTURES["jra_official"]
JRA_URL = NAR_URL = None
JRA_URL = JRA["source_url"]
NAR_URL = NAR["source_url"]


def _copy(record: dict[str, object], **changes: object) -> dict[str, object]:
    value = copy.deepcopy(record)
    value.update(changes)
    return value


def _official(record: dict[str, object], **changes: object) -> dict[str, object]:
    value = _copy(
        record,
        evidence_class="REAL_PUBLIC_WEB_RECORD",
        allowed_scope="private_shadow",
    )
    value.update(changes)
    return value


def _secondary(record: dict[str, object], **changes: object) -> dict[str, object]:
    value = _copy(
        record,
        source_url="https://race.netkeiba.com/opaque/race-result",
        source_authority="secondary",
        jurisdiction="JRA",
        evidence_class="PUBLIC_WEB_SECONDARY",
        allowed_scope="shadow_only",
    )
    value.update(changes)
    return value


def _manifest(
    record: dict[str, object],
    *,
    source_authority: str = "official",
    jurisdiction: str | None = None,
    evidence_class: str = "REAL_PUBLIC_WEB_RECORD",
    allowed_scope: str = "private_shadow",
    parsed_row_count: int = 2,
    content_sha256: str = "a" * 64,
    settled_payback_rows: int = 0,
    settled_race_ids: list[str] | tuple[str, ...] = (),
    cash_authorized: bool = False,
) -> dict[str, object]:
    return {
        "source_authority": source_authority,
        "jurisdiction": jurisdiction or record["jurisdiction"],
        "evidence_class": evidence_class,
        "allowed_scope": allowed_scope,
        "parsed_row_count": parsed_row_count,
        "content_sha256": content_sha256,
        "settled_payback_rows": settled_payback_rows,
        "settled_race_ids": list(settled_race_ids),
        "cash_authorized": cash_authorized,
    }


def _official_manifests(
    *,
    jra_rows: int = 2,
    nar_rows: int = 2,
    jra_payback: int = 0,
    nar_payback: int = 0,
) -> dict[str, dict[str, object]]:
    return {
        JRA_URL: _manifest(
            JRA,
            parsed_row_count=jra_rows,
            content_sha256="b" * 64,
            settled_payback_rows=jra_payback,
            settled_race_ids=[JRA["race_id"]] if jra_payback else [],
        ),
        NAR_URL: _manifest(
            NAR,
            parsed_row_count=nar_rows,
            content_sha256="c" * 64,
            settled_payback_rows=nar_payback,
            settled_race_ids=[NAR["race_id"]] if nar_payback else [],
        ),
    }


def test_empty_records_are_a_valid_redacted_not_ready_audit():
    report = audit_records([], _official_manifests())

    assert isinstance(report, AuditReport)
    assert report.coverage_start is None
    assert report.coverage_end is None
    assert report.record_count == 0
    assert report.race_count == 0
    assert report.duplicate_count == 0
    assert dict(report.missingness) == {
        "surface": 0,
        "track_condition": 0,
        "odds": 0,
        "body_weight_kg": 0,
    }
    assert report.timestamp_ordered is True
    assert report.cutoff_violations == 0
    assert report.max_odds_snapshot_age_seconds is None
    assert report.settled_payback_rows == 0
    assert report.content_hashes == ("b" * 64, "c" * 64)
    assert report.evidence_classes == ("REAL_PUBLIC_WEB_RECORD",)
    assert report.allowed_scopes == ("private_shadow",)
    assert report.cash_authorized is False
    assert report.model_ready is False
    assert set(report.blockers) >= {
        "NO_NORMALIZED_ACTUAL_RECORDS",
        "NO_SETTLED_PAYBACK",
        "NO_OBSERVED_ODDS",
    }
    assert not hasattr(report, "runners")
    assert "runner" not in repr(report).casefold()


def test_current_actual_audit_accepts_two_official_manifests_without_records():
    manifests = {
        JRA_URL: _manifest(
            JRA,
            parsed_row_count=12,
            content_sha256="85ff5415dfdd66fc5dd0b59fedb14eb8b2dbbb8d28e7e28effa29165539bd012",
        ),
        NAR_URL: _manifest(
            NAR,
            parsed_row_count=46,
            content_sha256="f245030f4608055c2fa24e2910d51edcd029f2292c9cfbe66d2911604e1e1c5b",
        ),
    }
    report = audit_records([], manifests)
    assert report.record_count == 0
    assert report.model_ready is False
    assert report.cash_authorized is False


def test_two_distinct_official_races_with_odds_and_payback_are_model_ready():
    nar = _official(
        NAR,
        runners=[
            {"runner_id": "runner-nar-01", "horse_number": 1, "odds": 2.0, "body_weight_kg": 480.0},
            {"runner_id": "runner-nar-02", "horse_number": 2, "odds": 4.0, "body_weight_kg": 470.0},
        ],
    )
    jra = _official(
        JRA,
        runners=[
            {"runner_id": "runner-jra-01", "horse_number": 1, "odds": 3.0, "body_weight_kg": 481.0},
            {"runner_id": "runner-jra-02", "horse_number": 2, "odds": 5.0, "body_weight_kg": 471.0},
        ],
    )
    manifests = _official_manifests(jra_payback=1, nar_payback=1)

    report = audit_records([nar, jra], manifests)

    assert report.record_count == 2
    assert report.race_count == 2
    assert report.model_ready is True
    assert report.blockers == ()
    assert report.max_odds_snapshot_age_seconds == 60


def test_later_snapshot_of_same_race_is_allowed_and_missingness_is_counted():
    first = _official(
        NAR,
        runners=[
            {"runner_id": "runner-nar-01", "horse_number": 1, "odds": None, "body_weight_kg": None},
            {"runner_id": "runner-nar-02", "horse_number": 2, "odds": 4.0, "body_weight_kg": None},
        ],
    )
    later = _copy(
        first,
        record_id="record-nar-later",
        event_id="event-nar-later",
        snapshot_at="2026-08-09T10:56:00+09:00",
        cutoff_at="2026-08-09T10:57:00+09:00",
    )
    report = audit_records([first, later], {NAR_URL: _manifest(NAR)})

    assert report.record_count == 2
    assert report.race_count == 1
    assert dict(report.missingness) == {
        "surface": 2,
        "track_condition": 2,
        "odds": 2,
        "body_weight_kg": 4,
    }


@pytest.mark.parametrize(
    "mutator",
    [
        lambda records, manifests: records,
        lambda records, manifests: records,
    ],
)
def test_missing_manifest_is_rejected(mutator):
    records = [_official(NAR)]
    manifests = {}
    with pytest.raises(AuditRejected, match="manifest"):
        audit_records(mutator(records, manifests), manifests)


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_authority", "secondary"),
        ("jurisdiction", "JRA"),
        ("evidence_class", "PUBLIC_WEB_SECONDARY"),
        ("allowed_scope", "shadow_only"),
    ],
)
def test_manifest_scope_metadata_must_match_record_exactly(field, value):
    records = [_official(NAR)]
    manifests = {NAR_URL: _manifest(NAR, **{field: value})}
    with pytest.raises(AuditRejected, match="manifest"):
        audit_records(records, manifests)


@pytest.mark.parametrize(
    "field,value",
    [
        ("content_sha256", "not-a-sha256"),
        ("parsed_row_count", -1),
        ("parsed_row_count", True),
        ("parsed_row_count", "2"),
        ("settled_payback_rows", -1),
        ("settled_payback_rows", False),
        ("settled_payback_rows", "1"),
    ],
)
def test_manifest_hash_count_and_bool_types_are_rejected(field, value):
    records = [_official(NAR)]
    manifests = {NAR_URL: _manifest(NAR, **{field: value})}
    with pytest.raises(AuditRejected, match="manifest"):
        audit_records(records, manifests)


def test_cash_authorized_manifest_is_rejected_before_model_ready():
    with pytest.raises(AuditRejected, match="cash"):
        audit_records(
            [],
            {NAR_URL: _manifest(NAR, cash_authorized=True)},
        )


def test_secondary_cannot_be_promoted_to_official_or_make_model_ready():
    secondary = _secondary(NAR)
    manifests = {
        secondary["source_url"]: _manifest(
            secondary,
            source_authority="secondary",
            jurisdiction="JRA",
            evidence_class="PUBLIC_WEB_SECONDARY",
            allowed_scope="shadow_only",
        )
    }
    report = audit_records([secondary], manifests)
    assert report.model_ready is False
    assert report.allowed_scopes == ("shadow_only",)
    with pytest.raises(AuditRejected, match="manifest"):
        audit_records(
            [secondary],
            {
                secondary["source_url"]: _manifest(
                    secondary,
                    source_authority="official",
                    jurisdiction="JRA",
                    evidence_class="REAL_PUBLIC_WEB_RECORD",
                    allowed_scope="private_shadow",
                )
            },
        )


def test_records_must_be_in_snapshot_order():
    first = _official(NAR)
    later = _copy(
        first,
        record_id="record-nar-later",
        event_id="event-nar-later",
        snapshot_at="2026-08-09T10:56:00+09:00",
        cutoff_at="2026-08-09T10:57:00+09:00",
    )
    with pytest.raises(AuditRejected, match="order"):
        audit_records([later, first], {NAR_URL: _manifest(NAR)})


def test_duplicate_semantic_snapshot_is_rejected():
    duplicate = _copy(
        _official(NAR),
        record_id="record-nar-duplicate",
        event_id="event-nar-duplicate",
    )
    with pytest.raises(AuditRejected, match="duplicate"):
        audit_records([_official(NAR), duplicate], {NAR_URL: _manifest(NAR)})


@pytest.mark.parametrize(
    "changes",
    [
        {"snapshot_at": "2026-08-09T10:56:00+09:00", "cutoff_at": "2026-08-09T10:55:00+09:00"},
        {"cutoff_at": "2026-08-09T11:01:00+09:00"},
    ],
)
def test_cutoff_and_race_time_leaks_are_rejected(changes):
    with pytest.raises(AuditRejected, match="timestamp|cutoff"):
        audit_records([_official(NAR, **changes)], {NAR_URL: _manifest(NAR)})


def test_report_is_frozen_and_nested_metadata_is_immutable():
    report = audit_records([], _official_manifests())
    with pytest.raises((AttributeError, TypeError)):
        report.record_count = 3
    with pytest.raises((TypeError, AttributeError)):
        report.missingness["odds"] = 3


def test_empty_manifest_mapping_is_rejected():
    with pytest.raises(AuditRejected, match="manifest"):
        audit_records([], {})


def test_secondary_odds_and_payback_cannot_unlock_official_readiness():
    secondary = _secondary(
        NAR,
        runners=[
            {"runner_id": "runner-secondary-01", "horse_number": 1, "odds": 2.0, "body_weight_kg": 480.0},
            {"runner_id": "runner-secondary-02", "horse_number": 2, "odds": 4.0, "body_weight_kg": 470.0},
        ],
    )
    manifests = _official_manifests()
    manifests[secondary["source_url"]] = _manifest(
        secondary,
        source_authority="secondary",
        jurisdiction="JRA",
        evidence_class="PUBLIC_WEB_SECONDARY",
        allowed_scope="shadow_only",
        settled_payback_rows=1,
        settled_race_ids=[secondary["race_id"]],
    )
    report = audit_records([_official(NAR), secondary, _official(JRA)], manifests)

    assert report.model_ready is False
    assert report.settled_payback_rows == 0
    assert "NO_SETTLED_PAYBACK" in report.blockers
    assert "NO_OBSERVED_ODDS" in report.blockers


def test_same_race_at_timestamp_cannot_satisfy_readiness_chronology():
    nar = _official(
        NAR,
        race_at="2026-08-09T12:00:00+09:00",
        runners=[
            {"runner_id": "runner-nar-01", "horse_number": 1, "odds": 2.0, "body_weight_kg": 480.0},
            {"runner_id": "runner-nar-02", "horse_number": 2, "odds": 4.0, "body_weight_kg": 470.0},
        ],
    )
    jra = _official(
        JRA,
        race_at="2026-08-09T12:00:00+09:00",
        runners=[
            {"runner_id": "runner-jra-01", "horse_number": 1, "odds": 3.0, "body_weight_kg": 481.0},
            {"runner_id": "runner-jra-02", "horse_number": 2, "odds": 5.0, "body_weight_kg": 471.0},
        ],
    )
    manifests = _official_manifests(jra_payback=1, nar_payback=1)
    report = audit_records([nar, jra], manifests)

    assert report.model_ready is False
    assert "INSUFFICIENT_CHRONOLOGY" in report.blockers


def test_unused_manifest_settlement_cannot_settle_an_observed_record():
    nar = _official(
        NAR,
        runners=[
            {"runner_id": "runner-nar-01", "horse_number": 1, "odds": 2.0, "body_weight_kg": 480.0},
            {"runner_id": "runner-nar-02", "horse_number": 2, "odds": 4.0, "body_weight_kg": 470.0},
        ],
    )
    jra = _official(
        JRA,
        runners=[
            {"runner_id": "runner-jra-01", "horse_number": 1, "odds": 3.0, "body_weight_kg": 481.0},
            {"runner_id": "runner-jra-02", "horse_number": 2, "odds": 5.0, "body_weight_kg": 471.0},
        ],
    )
    manifests = _official_manifests(jra_payback=1, nar_payback=1)
    manifests[JRA_URL]["settled_race_ids"] = ["other-jra-race"]
    manifests[NAR_URL]["settled_race_ids"] = ["other-nar-race"]
    report = audit_records([nar, jra], manifests)

    assert report.settled_payback_rows == 2
    assert report.model_ready is False
    assert "NO_MATCHING_SETTLED_PAYBACK" in report.blockers


def test_stale_official_records_remain_blocked():
    nar = _official(
        NAR,
        freshness={"status": "stale", "age_seconds": 3600},
        runners=[
            {"runner_id": "runner-nar-01", "horse_number": 1, "odds": 2.0, "body_weight_kg": 480.0},
            {"runner_id": "runner-nar-02", "horse_number": 2, "odds": 4.0, "body_weight_kg": 470.0},
        ],
    )
    jra = _official(
        JRA,
        freshness={"status": "stale", "age_seconds": 3601},
        runners=[
            {"runner_id": "runner-jra-01", "horse_number": 1, "odds": 3.0, "body_weight_kg": 481.0},
            {"runner_id": "runner-jra-02", "horse_number": 2, "odds": 5.0, "body_weight_kg": 471.0},
        ],
    )
    report = audit_records(
        [nar, jra],
        _official_manifests(jra_payback=1, nar_payback=1),
    )

    assert report.model_ready is False
    assert "STALE_OFFICIAL_RECORD" in report.blockers


def test_zero_row_official_manifest_remains_blocked():
    nar = _official(
        NAR,
        runners=[
            {"runner_id": "runner-nar-01", "horse_number": 1, "odds": 2.0, "body_weight_kg": 480.0},
            {"runner_id": "runner-nar-02", "horse_number": 2, "odds": 4.0, "body_weight_kg": 470.0},
        ],
    )
    jra = _official(
        JRA,
        runners=[
            {"runner_id": "runner-jra-01", "horse_number": 1, "odds": 3.0, "body_weight_kg": 481.0},
            {"runner_id": "runner-jra-02", "horse_number": 2, "odds": 5.0, "body_weight_kg": 471.0},
        ],
    )
    manifests = _official_manifests(jra_payback=1, nar_payback=1)
    manifests[JRA_URL]["parsed_row_count"] = 0
    report = audit_records([nar, jra], manifests)

    assert report.model_ready is False
    assert "NO_PARSED_OFFICIAL_ROWS" in report.blockers


@pytest.mark.parametrize(
    "changes",
    [
        {"settled_race_ids": None},
        {"settled_race_ids": "race-id"},
        {"settled_race_ids": ["race-id", "race-id"]},
        {"settled_race_ids": ["race-id"], "settled_payback_rows": 0},
        {"settled_race_ids": ["", "other"]},
    ],
)
def test_settled_race_ids_schema_and_count_are_rejected(changes):
    values = _manifest(NAR, settled_payback_rows=1, settled_race_ids=[NAR["race_id"]])
    values.update(changes)
    with pytest.raises(AuditRejected, match="settled"):
        audit_records([], {NAR_URL: values})
