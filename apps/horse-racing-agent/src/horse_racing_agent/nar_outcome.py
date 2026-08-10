from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
from pathlib import Path
import re
from typing import Iterable

from horse_racing_agent.ingest import _source_scope
from horse_racing_agent.nar_materialize import (
    _cell,
    _key,
    _path,
    _read_archive,
    _scope,
    _sha256_file,
    _timestamp,
    nar_race_id,
    nar_runner_id,
)


_REAL_SOURCE_URL = (
    "https://www.keiba.go.jp/KeibaWeb/DataDownload/"
    "RaceDataDownload?type=monthly&k_year=2026&k_month=8"
)
_REAL_SHA256 = "ca512328b477054738f0a926710c3c5c16b1e25d9f7e4ffaf7f9cfc9604c2149"
_REAL_CAPTURED_AT = "2026-08-10T10:37:13+09:00"
_REAL_PROVENANCE = frozenset({(_REAL_SOURCE_URL, _REAL_SHA256, _REAL_CAPTURED_AT)})
_ASCII_DIGITS = re.compile(r"[0-9]+\Z")


def _fail(message: str) -> None:
    raise ValueError(message)


def _positive_digits(value: str, message: str) -> int:
    if not isinstance(value, str):
        _fail(message)
    text = value.strip()
    if _ASCII_DIGITS.fullmatch(text) is None:
        _fail(message)
    try:
        parsed = int(text)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(message) from exc
    if parsed <= 0:
        _fail(message)
    return parsed


def _is_finite_positive_integer(value: object) -> bool:
    if type(value) is not int or value <= 0:
        return False
    try:
        return math.isfinite(float(value))
    except OverflowError:
        return False


def _payout_yen(value: str) -> int:
    """Parse one official payout as a finite, positive integer amount."""

    if not isinstance(value, str):
        _fail("payout is invalid")
    text = value.strip()
    if _ASCII_DIGITS.fullmatch(text) is None:
        _fail("payout is invalid")
    try:
        parsed = int(text)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("payout is invalid") from exc
    if not _is_finite_positive_integer(parsed):
        _fail("payout is invalid")
    return parsed


@dataclass(frozen=True, repr=False)
class WinPayout:
    _winner_runner_id: str
    _payout_yen_per_100: int

    def __post_init__(self) -> None:
        if not isinstance(self._winner_runner_id, str) or not self._winner_runner_id.strip():
            _fail("winner runner identity is invalid")
        if (
            not _is_finite_positive_integer(self._payout_yen_per_100)
        ):
            _fail("payout is invalid")


@dataclass(frozen=True, repr=False)
class WinOutcome:
    _race_id: str
    _market: str
    _status: str
    _source_url: str
    _source_authority: str
    _jurisdiction: str
    _evidence_class: str
    _captured_at: str
    _source_sha256: str
    _payouts: tuple[WinPayout, ...]

    def __post_init__(self) -> None:
        if not isinstance(self._race_id, str) or not self._race_id.strip():
            _fail("race identity is invalid")
        if self._market != "win" or self._status != "settled":
            _fail("outcome status is invalid")
        for value in (
            self._source_url,
            self._source_authority,
            self._jurisdiction,
            self._evidence_class,
            self._captured_at,
        ):
            if not isinstance(value, str) or not value.strip():
                _fail("outcome metadata is invalid")
        if (
            not isinstance(self._source_sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", self._source_sha256) is None
        ):
            _fail("outcome hash is invalid")
        if not isinstance(self._payouts, tuple) or not self._payouts:
            _fail("outcome payouts are invalid")
        if not all(isinstance(item, WinPayout) for item in self._payouts):
            _fail("outcome payouts are invalid")


def _validate_source(source_url: str, evidence_class: str) -> None:
    if not isinstance(source_url, str) or not source_url.strip():
        _fail("source metadata is invalid")
    try:
        _source_scope(source_url, "official", "NAR")
    except (TypeError, ValueError):
        _fail("source metadata is invalid")
    _scope(evidence_class)


def _horselist_winners(rows: Iterable[dict[str, str]]) -> tuple[dict[tuple[str, str, int], set[int]], dict[tuple[str, str, int], set[int]]]:
    winners: dict[tuple[str, str, int], set[int]] = {}
    horses: dict[tuple[str, str, int], set[int]] = {}
    for row in rows:
        key = _key(row)
        horse_number = _positive_digits(_cell(row, "馬番"), "horse number is invalid")
        placement = _cell(row, "着順").strip()
        race_horses = horses.setdefault(key, set())
        if horse_number in race_horses:
            _fail("duplicate horse key")
        race_horses.add(horse_number)
        if placement == "1":
            winners.setdefault(key, set()).add(horse_number)
    return winners, horses


def _payback_winners(rows: Iterable[dict[str, str]]) -> dict[tuple[str, str, int], dict[int, int]]:
    settled: dict[tuple[str, str, int], dict[int, int]] = {}
    for row in rows:
        key = _key(row)
        winner_text = _cell(row, "単勝組番").strip()
        payout_text = _cell(row, "単勝払戻金（円）").strip()
        if not winner_text and not payout_text:
            continue
        if not winner_text or not payout_text:
            _fail("payout is invalid")
        winner = _positive_digits(winner_text, "winner number is invalid")
        payout = _payout_yen(payout_text)
        race_payouts = settled.setdefault(key, {})
        if winner in race_payouts:
            _fail("duplicate or conflicting winner row")
        race_payouts[winner] = payout
    return settled


def materialize_nar_win_outcomes(
    race_zip_path: str | Path,
    *,
    captured_at: str | datetime,
    expected_sha256: str,
    source_url: str,
    evidence_class: str,
) -> tuple[WinOutcome, ...]:
    """Parse official NAR horselist/payback rows into settled win outcomes."""

    path = _path(race_zip_path)
    captured = _timestamp(captured_at)
    _validate_source(source_url, evidence_class)
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
        _fail("expected archive hash is invalid")
    archive_sha256 = expected_sha256.casefold()
    captured_iso = captured.isoformat()
    if evidence_class == "REAL_PUBLIC_WEB_RECORD" and (
        source_url,
        archive_sha256,
        captured_iso,
    ) not in _REAL_PROVENANCE:
        _fail("real provenance is not accepted")

    parsed = _read_archive(path, archive_sha256, {"horse", "payback"})
    winners, horses = _horselist_winners(parsed["horse"])
    settled = _payback_winners(parsed["payback"])

    outcomes: list[WinOutcome] = []
    for key, race_payouts in settled.items():
        horse_numbers = horses.get(key)
        if horse_numbers is None:
            _fail("payback horse join is missing")
        winner_numbers = winners.get(key, set())
        if set(race_payouts) != winner_numbers:
            _fail("settled winner set does not match horselist")
        race_id = nar_race_id(*key)
        payouts = tuple(
            WinPayout(nar_runner_id(race_id, horse_number), race_payouts[horse_number])
            for horse_number in sorted(race_payouts)
        )
        outcomes.append(
            WinOutcome(
                _race_id=race_id,
                _market="win",
                _status="settled",
                _source_url=source_url,
                _source_authority="official",
                _jurisdiction="NAR",
                _evidence_class=evidence_class,
                _captured_at=captured_iso,
                _source_sha256=archive_sha256,
                _payouts=payouts,
            )
        )

    if _sha256_file(path).casefold() != archive_sha256:
        _fail("archive input mutated")
    return tuple(sorted(outcomes, key=lambda item: item._race_id))


def redacted_summary(outcomes: Iterable[WinOutcome]) -> dict[str, object]:
    """Return only aggregate counts, source hash, and status."""

    values = tuple(outcomes)
    if not all(isinstance(item, WinOutcome) for item in values):
        _fail("outcomes are invalid")
    hashes = {item._source_sha256 for item in values}
    statuses = {item._status for item in values}
    return {
        "outcome_count": len(values),
        "winner_payout_count": sum(len(item._payouts) for item in values),
        "source_sha256": next(iter(hashes)) if len(hashes) == 1 else ("mixed" if hashes else None),
        "status": next(iter(statuses)) if len(statuses) == 1 else ("mixed" if statuses else "unsettled"),
    }
