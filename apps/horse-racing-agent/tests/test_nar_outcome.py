from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from horse_racing_agent.nar_materialize import nar_race_id, nar_runner_id
from horse_racing_agent.nar_outcome import (
    materialize_nar_win_outcomes,
    redacted_summary,
)


HORSE_HEADERS = ["競馬場", "競走年月日", "レース番号", "馬番", "着順"]
PAYBACK_HEADERS = [
    "競馬場",
    "競走年月日",
    "レース番号",
    "単勝組番",
    "単勝払戻金（円）",
]
CAPTURED_AT = "2026-08-10T10:37:13+09:00"
SOURCE_URL = (
    "https://www.keiba.go.jp/KeibaWeb/DataDownload/"
    "RaceDataDownload?type=monthly&k_year=2026&k_month=8"
)


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


def _rows(
    *,
    horses: list[dict[str, str]] | None = None,
    paybacks: list[dict[str, str]] | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    if horses is None:
        horses = [
            {"競馬場": "01", "競走年月日": "20260809", "レース番号": "1", "馬番": "1", "着順": "1"},
            {"競馬場": "01", "競走年月日": "20260809", "レース番号": "1", "馬番": "2", "着順": "2"},
            {"競馬場": "01", "競走年月日": "20260809", "レース番号": "2", "馬番": "1", "着順": "1"},
            {"競馬場": "01", "競走年月日": "20260809", "レース番号": "2", "馬番": "2", "着順": "1"},
            {"競馬場": "01", "競走年月日": "20260809", "レース番号": "2", "馬番": "3", "着順": "2"},
            {"競馬場": "01", "競走年月日": "20260809", "レース番号": "3", "馬番": "1", "着順": "1"},
        ]
    if paybacks is None:
        paybacks = [
            {"競馬場": "01", "競走年月日": "20260809", "レース番号": "1", "単勝組番": "1", "単勝払戻金（円）": "100"},
            {"競馬場": "01", "競走年月日": "20260809", "レース番号": "2", "単勝組番": "1", "単勝払戻金（円）": "200"},
            {"競馬場": "01", "競走年月日": "20260809", "レース番号": "2", "単勝組番": "2", "単勝払戻金（円）": "300"},
            {"競馬場": "01", "競走年月日": "20260809", "レース番号": "3", "単勝組番": "", "単勝払戻金（円）": ""},
        ]
    return horses, paybacks


def _build_zip(
    tmp_path: Path,
    *,
    horses: list[dict[str, str]] | None = None,
    paybacks: list[dict[str, str]] | None = None,
    entries: dict[str, bytes] | None = None,
    extra_entries: int = 0,
) -> Path:
    if entries is None:
        horses, paybacks = _rows(horses=horses, paybacks=paybacks)
        entries = {
            "horselist.csv": _csv_bytes(HORSE_HEADERS, horses),
            "payback.csv": _csv_bytes(PAYBACK_HEADERS, paybacks),
        }
    path = tmp_path / "nar-race.zip"
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_zip(path, entries, extra_entries=extra_entries)
    return path


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _materialize(path: Path, *, evidence_class: str = "SYNTHETIC_TEST"):
    return materialize_nar_win_outcomes(
        path,
        captured_at=CAPTURED_AT,
        expected_sha256=_hash(path),
        source_url=SOURCE_URL,
        evidence_class=evidence_class,
    )


def test_materializes_settled_win_outcomes_and_omits_unsettled_races(tmp_path: Path):
    path = _build_zip(tmp_path)

    outcomes = _materialize(path)

    assert len(outcomes) == 2
    assert sum(len(outcome._payouts) for outcome in outcomes) == 3
    assert all(outcome._market == "win" for outcome in outcomes)
    assert all(outcome._status == "settled" for outcome in outcomes)
    assert all(outcome._source_authority == "official" for outcome in outcomes)
    assert all(outcome._jurisdiction == "NAR" for outcome in outcomes)


def test_dead_heat_has_distinct_winners_and_deterministic_opaque_ids(tmp_path: Path):
    path = _build_zip(tmp_path)

    first = _materialize(path)
    second = _materialize(path)

    assert first == second
    dead_heat = next(outcome for outcome in first if len(outcome._payouts) == 2)
    assert len(dead_heat._payouts) == 2
    assert [item._winner_runner_id for item in dead_heat._payouts] == [
        nar_runner_id(dead_heat._race_id, 1),
        nar_runner_id(dead_heat._race_id, 2),
    ]
    assert dead_heat._race_id == nar_race_id("01", "20260809", 2)


@pytest.mark.parametrize(
    "change",
    [
        lambda horses, paybacks: paybacks.__setitem__(0, {**paybacks[0], "単勝組番": "2"}),
        lambda horses, paybacks: paybacks.__setitem__(0, {**paybacks[0], "単勝組番": "9"}),
        lambda horses, paybacks: paybacks.append(
            {"競馬場": "99", "競走年月日": "20260809", "レース番号": "9", "単勝組番": "1", "単勝払戻金（円）": "100"}
        ),
        lambda horses, paybacks: horses.append({**horses[0]}),
        lambda horses, paybacks: paybacks.append({**paybacks[0]}),
        lambda horses, paybacks: paybacks.append({**paybacks[0], "単勝払戻金（円）": "101"}),
    ],
)
def test_rejects_join_mismatch_duplicate_or_conflicting_rows(tmp_path: Path, change):
    horses, paybacks = _rows()
    change(horses, paybacks)
    path = _build_zip(tmp_path, horses=horses, paybacks=paybacks)

    with pytest.raises(ValueError, match="winner|join|duplicate|conflict|settled"):
        _materialize(path)


@pytest.mark.parametrize(
    ("winner", "payout"),
    [("0", "100"), ("1.0", "100"), ("1", "0"), ("1", "100.5"), ("1", "nan")],
)
def test_rejects_invalid_winner_or_payout(tmp_path: Path, winner: str, payout: str):
    horses, paybacks = _rows()
    paybacks[0] = {**paybacks[0], "単勝組番": winner, "単勝払戻金（円）": payout}
    path = _build_zip(tmp_path, horses=horses, paybacks=paybacks)

    with pytest.raises(ValueError, match="winner|payout|numeric|invalid"):
        _materialize(path)


def test_rejects_arbitrary_real_provenance_but_accepts_synthetic(tmp_path: Path):
    path = _build_zip(tmp_path)

    assert _materialize(path)
    with pytest.raises(ValueError, match="provenance"):
        _materialize(path, evidence_class="REAL_PUBLIC_WEB_RECORD")


def test_repr_and_redacted_summary_never_expose_ids_or_payout_values(tmp_path: Path):
    outcomes = _materialize(_build_zip(tmp_path))

    rendered = repr(outcomes) + repr(outcomes[0]._payouts[0])
    summary = redacted_summary(outcomes)
    assert "nar-race-" not in rendered
    assert "nar-runner-" not in rendered
    assert outcomes[0]._race_id not in rendered
    assert str(outcomes[0]._payouts[0]._payout_yen_per_100) not in rendered
    assert set(summary) == {"outcome_count", "winner_payout_count", "source_sha256", "status"}
    assert summary["outcome_count"] == 2
    assert summary["winner_payout_count"] == 3
    assert summary["status"] == "settled"
    summary_text = repr(summary)
    assert "nar-race-" not in summary_text
    assert "nar-runner-" not in summary_text
    assert outcomes[0]._race_id not in summary_text
    assert str(outcomes[0]._payouts[0]._payout_yen_per_100) not in summary_text


def test_rejects_hash_and_zip_safety_before_parsing(tmp_path: Path):
    path = _build_zip(tmp_path)
    with pytest.raises(ValueError, match="hash"):
        materialize_nar_win_outcomes(
            path,
            captured_at=CAPTURED_AT,
            expected_sha256="0" * 64,
            source_url=SOURCE_URL,
            evidence_class="SYNTHETIC_TEST",
        )

    unsafe = _build_zip(tmp_path / "unsafe", entries={"../escape.csv": b"x"})
    with pytest.raises(ValueError, match="ZIP"):
        _materialize(unsafe)

    too_many = _build_zip(tmp_path / "many", extra_entries=8)
    with pytest.raises(ValueError, match="ZIP"):
        _materialize(too_many)
