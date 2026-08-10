from __future__ import annotations

import csv
from datetime import datetime, timedelta
import hashlib
import io
import math
from pathlib import Path, PurePosixPath
from typing import Iterable
from zipfile import ZipFile
import zipfile
from zoneinfo import ZoneInfo

from horse_racing_agent.store import validate_normalized_race


_JST = ZoneInfo("Asia/Tokyo")
_ODDS_URL = "https://www.keiba.go.jp/KeibaWeb/DataDownload/OddsDataDownload?type=daily"
_REAL_PROVENANCE = frozenset(
    {
        (
            "60c8fb659d6b31369453bf6121576d1af082ddc274e3380dd19e3135403d0135",
            "feaa43d6bdaa019aa748a7ce05f527235647531bc90bfcc38fb0eadb5dc8c515",
            "2026-08-10T10:46:23+09:00",
        )
    }
)
_MAX_ENTRIES = 8
_MAX_MEMBER_BYTES = 50 * 1024 * 1024
_BOM = b"\xef\xbb\xbf"
_RACE_HEADERS = {"競馬場", "競走年月日", "レース番号", "発走時刻", "芝ダート区分", "馬場"}
_HORSE_HEADERS = {"競馬場", "競走年月日", "レース番号", "馬番", "馬体重"}
_OUTCOME_HORSE_HEADERS = {"競馬場", "競走年月日", "レース番号", "馬番", "着順"}
_PAYBACK_HEADERS = {"競馬場", "競走年月日", "レース番号", "単勝組番", "単勝払戻金（円）"}
_ODDS_HEADERS = {"競馬場", "競走年月日", "レース番号", "賭式", "番号1", "番号2", "番号3", "オッズ"}


def _fail(message: str) -> None:
    raise ValueError(message)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path(path: str | Path) -> Path:
    if not isinstance(path, (str, Path)):
        _fail("archive path is invalid")
    resolved = Path(path)
    if not resolved.exists() or not resolved.is_file():
        _fail("archive path is invalid")
    return resolved


def _timestamp(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("snapshot timestamp is invalid") from exc
    else:
        _fail("snapshot timestamp is invalid")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail("snapshot timestamp is invalid")
    return parsed.astimezone(_JST)


def _safe_member(info: zipfile.ZipInfo) -> None:
    name = info.filename
    parts = PurePosixPath(name).parts
    mode = (info.external_attr >> 16) & 0o170000
    if not name or "\\" in name or PurePosixPath(name).is_absolute() or ".." in parts:
        _fail("ZIP member path is unsafe")
    if mode == 0o120000:
        _fail("ZIP member symlink is unsafe")
    if info.file_size > _MAX_MEMBER_BYTES:
        _fail("ZIP member is too large")


def _role(headers: list[str]) -> str | None:
    if len(headers) != len(set(headers)):
        _fail("duplicate CSV headers")
    fields = set(headers)
    if _RACE_HEADERS <= fields:
        return "race"
    if _HORSE_HEADERS <= fields or _OUTCOME_HORSE_HEADERS <= fields:
        return "horse"
    if _PAYBACK_HEADERS <= fields:
        return "payback"
    if _ODDS_HEADERS <= fields:
        return "odds"
    return None


def _read_archive(path: Path, expected_sha256: str, required: set[str]) -> dict[str, list[dict[str, str]]]:
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
        _fail("expected archive hash is invalid")
    actual = _sha256_file(path)
    if actual.casefold() != expected_sha256.casefold():
        _fail("archive hash mismatch")
    parsed: dict[str, list[dict[str, str]]] = {}
    try:
        with ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > _MAX_ENTRIES:
                _fail("ZIP entry limit exceeded")
            for info in infos:
                _safe_member(info)
                payload = archive.read(info)
                if len(payload) > _MAX_MEMBER_BYTES:
                    _fail("ZIP member is too large")
                if not info.filename.lower().endswith(".csv"):
                    continue
                if not payload.startswith(_BOM):
                    _fail("CSV encoding must be UTF-8 with BOM")
                try:
                    text = payload[3:].decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise ValueError("CSV encoding is invalid") from exc
                reader = csv.DictReader(io.StringIO(text, newline=""))
                headers = list(reader.fieldnames or [])
                kind = _role(headers)
                if kind is None:
                    continue
                if kind in parsed:
                    _fail("duplicate required CSV")
                rows: list[dict[str, str]] = []
                for row in reader:
                    if None in row:
                        _fail("CSV row shape is invalid")
                    rows.append({key: value for key, value in row.items() if key is not None})
                parsed[kind] = rows
    except zipfile.BadZipFile as exc:
        raise ValueError("ZIP archive is invalid") from exc
    missing = required - parsed.keys()
    if missing:
        _fail("required CSV is missing")
    return parsed


def _date(value: str) -> str:
    if not isinstance(value, str) or len(value) != 8 or not value.isdigit():
        _fail("date is invalid")
    try:
        datetime.strptime(value, "%Y%m%d")
    except ValueError as exc:
        raise ValueError("date is invalid") from exc
    return value


def _positive_int(value: str, message: str) -> int:
    if not isinstance(value, str) or not value.isdigit() or int(value) <= 0:
        _fail(message)
    return int(value)


def _cell(row: dict[str, str], field: str) -> str:
    value = row.get(field)
    if not isinstance(value, str):
        _fail(f"{field} is invalid")
    return value


def _race_time(date: str, value: str) -> datetime:
    if not isinstance(value, str) or len(value) != 4 or not value.isdigit():
        _fail("time is invalid")
    hour, minute = int(value[:2]), int(value[2:])
    if hour > 23 or minute > 59:
        _fail("time is invalid")
    return datetime.strptime(f"{date}{value}", "%Y%m%d%H%M").replace(tzinfo=_JST)


def _number(value: str, *, nullable: bool, positive: bool = True) -> float | None:
    value = value.strip() if isinstance(value, str) else ""
    if not value and nullable:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("numeric field is invalid") from exc
    if not math.isfinite(parsed) or (positive and parsed <= 0):
        _fail("numeric field is invalid")
    return parsed


def _odds(value: str) -> float | None:
    if not isinstance(value, str):
        _fail("odds numeric field is invalid")
    value = value.strip()
    if not value:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("odds numeric field is invalid") from exc
    if not math.isfinite(parsed):
        _fail("odds numeric field is invalid")
    return parsed if parsed > 0 else None


def _key(row: dict[str, str]) -> tuple[str, str, int]:
    venue = row.get("競馬場")
    date = row.get("競走年月日")
    number = row.get("レース番号")
    if not all(isinstance(value, str) for value in (venue, date, number)):
        _fail("race key is invalid")
    venue = venue.strip()
    if not venue:
        _fail("race venue is invalid")
    return venue, _date(date.strip()), _positive_int(number.strip(), "race number is invalid")


def _digest(*parts: object) -> str:
    return hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()


def nar_race_id(venue: str, date: str, race_number: int) -> str:
    """Return the deterministic opaque identifier for one NAR race key."""

    return "nar-race-" + _digest(venue, date, race_number)


def nar_runner_id(race_id: str, horse_number: int) -> str:
    """Return the deterministic opaque identifier for one NAR runner key."""

    return "nar-runner-" + _digest(race_id, horse_number)


def _scope(evidence_class: str) -> str:
    if evidence_class == "SYNTHETIC_TEST":
        return "test_only"
    if evidence_class == "REAL_PUBLIC_WEB_RECORD":
        return "private_shadow"
    _fail("evidence class is invalid")


def _parse_rows(
    races: Iterable[dict[str, str]],
    horses: Iterable[dict[str, str]],
    odds: Iterable[dict[str, str]],
    snapshot: datetime,
    odds_sha256: str,
    evidence_class: str,
) -> tuple[dict[str, object], ...]:
    race_map: dict[tuple[str, str, int], dict[str, object]] = {}
    for row in races:
        key = _key(row)
        if key in race_map:
            _fail("duplicate race key")
        date = key[1]
        race_map[key] = {
            "race_at": _race_time(date, _cell(row, "発走時刻").strip()),
            "surface": _cell(row, "芝ダート区分").strip() or None,
            "track_condition": _cell(row, "馬場").strip() or None,
            "runners": {},
        }
    horse_map: dict[tuple[str, str, int], dict[int, float | None]] = {}
    for row in horses:
        key = _key(row)
        number = _positive_int(_cell(row, "馬番").strip(), "horse number is invalid")
        runners = horse_map.setdefault(key, {})
        if number in runners:
            _fail("duplicate horse key")
        runners[number] = _number(row["馬体重"], nullable=True)
        if key not in race_map:
            _fail("horse race key is not present")
    for key, race in race_map.items():
        race["runners"] = horse_map.get(key, {})

    win_odds: dict[tuple[str, str, int], dict[int, float]] = {}
    seen_exact_keys: set[tuple[tuple[str, str, int], int]] = set()
    extras: set[tuple[str, str, int]] = set()
    for row in odds:
        key = _key(row)
        if _cell(row, "賭式").strip() != "単勝":
            continue
        first = _cell(row, "番号1").strip()
        second = _cell(row, "番号2").strip()
        third = _cell(row, "番号3").strip()
        for component in (second, third):
            if component:
                _positive_int(component, "odds runner number is invalid")
        if not first:
            continue
        number = _positive_int(first, "odds runner number is invalid")
        if second or third:
            continue
        exact_key = (key, number)
        if exact_key in seen_exact_keys:
            _fail("duplicate odds key")
        seen_exact_keys.add(exact_key)
        odd = _odds(_cell(row, "オッズ"))
        if key not in race_map or number not in race_map[key]["runners"]:
            extras.add(key)
            continue
        if odd is None:
            continue
        keyed = win_odds.setdefault(key, {})
        if number in keyed:
            _fail("duplicate odds key")
        keyed[number] = odd

    records: list[dict[str, object]] = []
    scope = _scope(evidence_class)
    snapshot_iso = snapshot.isoformat()
    for key, race in race_map.items():
        runner_weights: dict[int, float | None] = race["runners"]
        odds_for_race = win_odds.get(key, {})
        if key in extras or not runner_weights or set(odds_for_race) != set(runner_weights):
            continue
        race_at: datetime = race["race_at"]
        cutoff_at = race_at - timedelta(minutes=10)
        if snapshot > cutoff_at:
            continue
        race_id = nar_race_id(key[0], key[1], key[2])
        event_id = "nar-event-" + _digest(race_id, "market=win", snapshot_iso, odds_sha256.casefold())
        record_id = "nar-record-" + _digest(race_id, "market=win", snapshot_iso, odds_sha256.casefold())
        runners = [
            {
                "runner_id": nar_runner_id(race_id, number),
                "horse_number": number,
                "odds": odds_for_race[number],
                "body_weight_kg": runner_weights[number],
            }
            for number in sorted(runner_weights)
        ]
        record = {
            "schema_version": 1,
            "record_id": record_id,
            "event_id": event_id,
            "race_id": race_id,
            "source_url": _ODDS_URL,
            "source_authority": "official",
            "jurisdiction": "NAR",
            "market": "win",
            "evidence_class": evidence_class,
            "allowed_scope": scope,
            "permission_document_verified": False,
            "raw_values_exported": False,
            "race_at": race_at.isoformat(),
            "snapshot_at": snapshot_iso,
            "cutoff_at": cutoff_at.isoformat(),
            "freshness": {"status": "fresh", "age_seconds": 0},
            "surface": race["surface"],
            "track_condition": race["track_condition"],
            "runners": runners,
        }
        records.append(validate_normalized_race(record))
    return tuple(sorted(records, key=lambda item: (item["race_at"], item["race_id"])))


def materialize_daily_win(
    race_zip_path: str | Path,
    odds_zip_path: str | Path,
    *,
    snapshot_at: str | datetime,
    expected_race_sha256: str,
    expected_odds_sha256: str,
    evidence_class: str,
) -> tuple[dict[str, object], ...]:
    """Materialize complete, cutoff-safe NAR ``単勝`` snapshots only."""

    race_path = _path(race_zip_path)
    odds_path = _path(odds_zip_path)
    snapshot = _timestamp(snapshot_at)
    scope = _scope(evidence_class)
    if not isinstance(expected_race_sha256, str) or not isinstance(expected_odds_sha256, str):
        _fail("expected archive hash is invalid")
    race_sha256 = expected_race_sha256.casefold()
    odds_sha256 = expected_odds_sha256.casefold()
    if evidence_class == "REAL_PUBLIC_WEB_RECORD" and (
        race_sha256,
        odds_sha256,
        snapshot.isoformat(),
    ) not in _REAL_PROVENANCE:
        _fail("real provenance is not accepted")
    race_csv = _read_archive(race_path, race_sha256, {"race", "horse"})
    odds_csv = _read_archive(odds_path, odds_sha256, {"odds"})
    records = _parse_rows(
        race_csv["race"],
        race_csv["horse"],
        odds_csv["odds"],
        snapshot,
        odds_sha256,
        evidence_class,
    )
    if _sha256_file(race_path).casefold() != race_sha256 or _sha256_file(odds_path).casefold() != odds_sha256:
        _fail("archive input mutated")
    return records
