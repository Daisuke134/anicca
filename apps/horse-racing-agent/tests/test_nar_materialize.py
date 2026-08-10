from __future__ import annotations

import csv
import hashlib
import io
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import pytest

from horse_racing_agent.nar_materialize import materialize_daily_win


RACE_HEADERS = [
    "競馬場",
    "競走年月日",
    "レース番号",
    "発走時刻",
    "芝ダート区分",
    "馬場",
]
HORSE_HEADERS = [
    "競馬場",
    "競走年月日",
    "レース番号",
    "馬番",
    "馬体重",
]
ODDS_HEADERS = [
    "競馬場",
    "競走年月日",
    "レース番号",
    "賭式",
    "番号1",
    "番号2",
    "番号3",
    "オッズ",
]
SNAPSHOT = "2026-08-10T10:00:00+09:00"
RACE_URL = "https://www.keiba.go.jp/KeibaWeb/DataDownload/RaceDataDownload?type=daily"
ODDS_URL = "https://www.keiba.go.jp/KeibaWeb/DataDownload/OddsDataDownload?type=daily"
EVIDENCE_PATH = Path(__file__).parents[3] / "docs/evidence/horse-racing/nar-daily-materialized-records.md"


def _csv_bytes(headers: list[str], rows: list[dict[str, str]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=headers, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return b"\xef\xbb\xbf" + stream.getvalue().encode("utf-8")


def _write_zip(path: Path, entries: dict[str, bytes], *, extra_entries: int = 0) -> None:
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        for name, payload in entries.items():
            archive.writestr(name, payload)
        for index in range(extra_entries):
            archive.writestr(f"extra-{index}.txt", b"unused")


def _source_rows(
    *,
    race_times: tuple[str, ...] = ("1200", "1230"),
    horses: tuple[int, ...] = (1, 2),
) -> tuple[dict[str, bytes], dict[str, bytes]]:
    race_rows = []
    horse_rows = []
    odds_rows = []
    for race_number, start in enumerate(race_times, start=1):
        race_key = {"競馬場": "01", "競走年月日": "20260810", "レース番号": str(race_number)}
        race_rows.append({**race_key, "発走時刻": start, "芝ダート区分": "ダ", "馬場": "良"})
        for horse_number in horses:
            horse_rows.append({**race_key, "馬番": str(horse_number), "馬体重": "480" if horse_number == 1 else ""})
            odds_rows.append(
                {
                    **race_key,
                    "賭式": "単勝",
                    "番号1": str(horse_number),
                    "番号2": "",
                    "番号3": "",
                    "オッズ": "2.5" if horse_number == 1 else "4.0",
                }
            )
    return (
        {
            "racelist.csv": _csv_bytes(RACE_HEADERS, race_rows),
            "horselist.csv": _csv_bytes(HORSE_HEADERS, horse_rows),
        },
        {"odds.csv": _csv_bytes(ODDS_HEADERS, odds_rows)},
    )


def _build_inputs(tmp_path: Path, *, odds_rows: list[dict[str, str]] | None = None) -> tuple[Path, Path]:
    race_entries, odds_entries = _source_rows()
    if odds_rows is not None:
        odds_entries["odds.csv"] = _csv_bytes(ODDS_HEADERS, odds_rows)
    race_zip = tmp_path / "race.zip"
    odds_zip = tmp_path / "odds.zip"
    _write_zip(race_zip, race_entries)
    _write_zip(odds_zip, odds_entries)
    return race_zip, odds_zip


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _materialize(race_zip: Path, odds_zip: Path):
    return materialize_daily_win(
        race_zip,
        odds_zip,
        snapshot_at=SNAPSHOT,
        expected_race_sha256=_hash(race_zip),
        expected_odds_sha256=_hash(odds_zip),
        evidence_class="SYNTHETIC_TEST",
    )


def test_materializes_complete_win_records_with_redacted_deterministic_shape(tmp_path: Path):
    race_zip, odds_zip = _build_inputs(tmp_path)
    records = _materialize(race_zip, odds_zip)

    assert len(records) == 2
    assert [len(record["runners"]) for record in records] == [2, 2]
    assert [record["market"] for record in records] == ["win", "win"]
    assert [runner["horse_number"] for runner in records[0]["runners"]] == [1, 2]
    assert records[0]["source_url"] == ODDS_URL
    assert records[0]["evidence_class"] == "SYNTHETIC_TEST"
    assert records[0]["allowed_scope"] == "test_only"
    assert records[0]["permission_document_verified"] is False
    assert records[0]["raw_values_exported"] is False
    assert records[0]["freshness"] == {"status": "fresh", "age_seconds": 0}
    assert records[0]["surface"] == "ダ"
    assert records[0]["track_condition"] == "良"
    assert records[0]["runners"][1]["body_weight_kg"] is None
    forbidden = {"馬名", "horse_name", "jockey", "trainer", "raw_payload", "odds_archive_hash"}
    assert not forbidden.intersection(records[0])
    assert not forbidden.intersection(records[0]["runners"][0])


def test_ids_and_order_are_deterministic_and_opaque(tmp_path: Path):
    race_zip, odds_zip = _build_inputs(tmp_path)
    first = _materialize(race_zip, odds_zip)
    second = _materialize(race_zip, odds_zip)
    assert first == second
    assert all(record["record_id"].startswith("nar-record-") for record in first)
    assert all(record["event_id"].startswith("nar-event-") for record in first)
    assert all(record["race_id"].startswith("nar-race-") for record in first)
    assert all(runner["runner_id"].startswith("nar-runner-") for runner in first[0]["runners"])
    for record in first:
        assert len(record["race_id"].removeprefix("nar-race-")) == 64
        assert all(len(runner["runner_id"].removeprefix("nar-runner-")) == 64 for runner in record["runners"])


def test_rejects_expected_hash_mismatch_before_parsing(tmp_path: Path):
    race_zip, odds_zip = _build_inputs(tmp_path)
    with pytest.raises(ValueError, match="hash"):
        materialize_daily_win(
            race_zip,
            odds_zip,
            snapshot_at=SNAPSHOT,
            expected_race_sha256="0" * 64,
            expected_odds_sha256=_hash(odds_zip),
            evidence_class="SYNTHETIC_TEST",
        )


def test_rejects_arbitrary_real_provenance_but_accepts_synthetic(tmp_path: Path):
    race_zip, odds_zip = _build_inputs(tmp_path)
    assert _materialize(race_zip, odds_zip)
    with pytest.raises(ValueError, match="provenance"):
        materialize_daily_win(
            race_zip,
            odds_zip,
            snapshot_at=SNAPSHOT,
            expected_race_sha256=_hash(race_zip),
            expected_odds_sha256=_hash(odds_zip),
            evidence_class="REAL_PUBLIC_WEB_RECORD",
        )


@pytest.mark.parametrize(
    "mutator",
    [
        lambda race_zip, odds_zip: _write_zip(race_zip, {"../escape.csv": b"x"}),
        lambda race_zip, odds_zip: _write_zip(race_zip, {"one.txt": b"x"}, extra_entries=8),
    ],
)
def test_rejects_zip_safety_violations(tmp_path: Path, mutator):
    race_zip, odds_zip = _build_inputs(tmp_path)
    mutator(race_zip, odds_zip)
    with pytest.raises(ValueError, match="ZIP"):
        _materialize(race_zip, odds_zip)


def test_rejects_non_bom_and_duplicate_required_csv(tmp_path: Path):
    race_entries, odds_entries = _source_rows()
    race_entries["racelist.csv"] = race_entries["racelist.csv"][3:]
    race_entries["racelist-copy.csv"] = _csv_bytes(RACE_HEADERS, [])
    race_zip = tmp_path / "race.zip"
    odds_zip = tmp_path / "odds.zip"
    _write_zip(race_zip, race_entries)
    _write_zip(odds_zip, odds_entries)
    with pytest.raises(ValueError, match="encoding|duplicate"):
        _materialize(race_zip, odds_zip)


def test_excludes_incomplete_and_non_win_markets_and_rejects_duplicate_win_key(tmp_path: Path):
    race_entries, odds_entries = _source_rows()
    odds = [
        {"競馬場": "01", "競走年月日": "20260810", "レース番号": "1", "賭式": "単勝", "番号1": "1", "番号2": "", "番号3": "", "オッズ": "2.5"},
        {"競馬場": "01", "競走年月日": "20260810", "レース番号": "1", "賭式": "単勝", "番号1": "1", "番号2": "", "番号3": "", "オッズ": "3.5"},
        {"競馬場": "01", "競走年月日": "20260810", "レース番号": "1", "賭式": "複勝", "番号1": "2", "番号2": "", "番号3": "", "オッズ": "1.5"},
        {"競馬場": "01", "競走年月日": "20260810", "レース番号": "2", "賭式": "単勝", "番号1": "1", "番号2": "", "番号3": "", "オッズ": "2.5"},
    ]
    odds_entries["odds.csv"] = _csv_bytes(ODDS_HEADERS, odds)
    race_zip = tmp_path / "race.zip"
    odds_zip = tmp_path / "odds.zip"
    _write_zip(race_zip, race_entries)
    _write_zip(odds_zip, odds_entries)
    with pytest.raises(ValueError, match="duplicate"):
        _materialize(race_zip, odds_zip)


def test_rejects_duplicate_exact_win_key_when_zero_precedes_positive(tmp_path: Path):
    odds_rows = [
        {"競馬場": "01", "競走年月日": "20260810", "レース番号": "1", "賭式": "単勝", "番号1": "1", "番号2": "", "番号3": "", "オッズ": "0.0"},
        {"競馬場": "01", "競走年月日": "20260810", "レース番号": "1", "賭式": "単勝", "番号1": "1", "番号2": "", "番号3": "", "オッズ": "2.5"},
        {"競馬場": "01", "競走年月日": "20260810", "レース番号": "1", "賭式": "単勝", "番号1": "2", "番号2": "", "番号3": "", "オッズ": "4.0"},
        {"競馬場": "01", "競走年月日": "20260810", "レース番号": "2", "賭式": "単勝", "番号1": "1", "番号2": "", "番号3": "", "オッズ": "2.5"},
        {"競馬場": "01", "競走年月日": "20260810", "レース番号": "2", "賭式": "単勝", "番号1": "2", "番号2": "", "番号3": "", "オッズ": "4.0"},
    ]
    race_zip, odds_zip = _build_inputs(tmp_path, odds_rows=odds_rows)
    with pytest.raises(ValueError, match="duplicate"):
        _materialize(race_zip, odds_zip)


def test_excludes_nonpositive_extra_runner_key_before_odds_filter(tmp_path: Path):
    odds_rows = [
        {"競馬場": "01", "競走年月日": "20260810", "レース番号": "1", "賭式": "単勝", "番号1": "1", "番号2": "", "番号3": "", "オッズ": "2.5"},
        {"競馬場": "01", "競走年月日": "20260810", "レース番号": "1", "賭式": "単勝", "番号1": "2", "番号2": "", "番号3": "", "オッズ": "4.0"},
        {"競馬場": "01", "競走年月日": "20260810", "レース番号": "1", "賭式": "単勝", "番号1": "99", "番号2": "", "番号3": "", "オッズ": "0.0"},
        {"競馬場": "01", "競走年月日": "20260810", "レース番号": "2", "賭式": "単勝", "番号1": "1", "番号2": "", "番号3": "", "オッズ": "2.5"},
        {"競馬場": "01", "競走年月日": "20260810", "レース番号": "2", "賭式": "単勝", "番号1": "2", "番号2": "", "番号3": "", "オッズ": "4.0"},
    ]
    race_zip, odds_zip = _build_inputs(tmp_path, odds_rows=odds_rows)
    records = _materialize(race_zip, odds_zip)
    assert len(records) == 1


def test_evidence_distinguishes_private_numeric_fields_from_redacted_export():
    text = " ".join(EVIDENCE_PATH.read_text().lower().split())
    assert "private mac-local normalized records" in text
    assert "numeric odds" in text
    assert "redacted evidence and `auditreport` export no numeric odds or weights" in text
    assert "the output contains deterministic opaque identifiers and normalized schema metadata only" not in text
    assert "it contains no horse/person names, odds values, body-weight values" not in text


def test_excludes_race_after_cutoff_without_inventing_zero(tmp_path: Path):
    race_entries, odds_entries = _source_rows(race_times=("1000", "1230"))
    race_zip = tmp_path / "race.zip"
    odds_zip = tmp_path / "odds.zip"
    _write_zip(race_zip, race_entries)
    _write_zip(odds_zip, odds_entries)
    records = _materialize(race_zip, odds_zip)
    assert len(records) == 1
    assert records[0]["race_at"].endswith("12:30:00+09:00")


def test_rejects_malformed_date_time_or_numeric_fields(tmp_path: Path):
    race_entries, odds_entries = _source_rows()
    rows = [
        {"競馬場": "01", "競走年月日": "20261399", "レース番号": "1", "発走時刻": "1200", "芝ダート区分": "ダ", "馬場": "良"},
    ]
    race_entries["racelist.csv"] = _csv_bytes(RACE_HEADERS, rows)
    race_zip = tmp_path / "race.zip"
    odds_zip = tmp_path / "odds.zip"
    _write_zip(race_zip, race_entries)
    _write_zip(odds_zip, odds_entries)
    with pytest.raises(ValueError, match="date|time|number|numeric"):
        _materialize(race_zip, odds_zip)
