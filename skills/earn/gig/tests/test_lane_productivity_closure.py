"""Fail-closed closure metadata for authoritative lane evidence."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import lane_productivity  # noqa: E402


def _empty_authoritative_state(tmp_path: Path) -> Path:
    (tmp_path / "applied.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "shuppin.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "paid-progress.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "evidence").mkdir()
    db = tmp_path / "connector-outbox.sqlite3"
    with sqlite3.connect(db) as connection:
        connection.execute(
            "CREATE TABLE connector_actions ("
            "action_id INTEGER PRIMARY KEY, state TEXT NOT NULL, "
            "updated_at INTEGER NOT NULL, seller_sent_at INTEGER)"
        )
    return tmp_path


def test_reader_exception_is_an_explicit_closure_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(lane_productivity, "STATE", _empty_authoritative_state(tmp_path))
    monkeypatch.setattr(
        lane_productivity,
        "_reply_evidence",
        lambda _since: (_ for _ in ()).throw(OSError("outbox unreadable")),
    )

    closure = lane_productivity.closure_snapshot(100)

    assert closure["reply"]["action_kind"] == "error"
    assert closure["reply"]["status"] == "error"
    assert closure["reply"]["collector_complete"] is False
    assert closure["reply"]["coverage_complete"] is False
    assert closure["reply"]["action_kind"] != "verified_noop"


def test_missing_authoritative_source_is_not_a_verified_noop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(lane_productivity, "STATE", tmp_path)

    closure = lane_productivity.closure_snapshot(100)

    assert closure["application"]["action_kind"] == "error"
    assert closure["application"]["status"] == "error"
    assert closure["application"]["collector_complete"] is False
    assert closure["application"]["coverage_complete"] is False


def test_readable_empty_authoritative_sources_remain_honest_noop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(lane_productivity, "STATE", _empty_authoritative_state(tmp_path))

    closure = lane_productivity.closure_snapshot(100)

    for lane in ("application", "delivery", "listing", "reply"):
        assert closure[lane]["action_kind"] == "verified_noop"
        assert closure[lane]["status"] == "success"
        assert closure[lane]["collector_complete"] is True
        assert closure[lane]["coverage_complete"] is True
        assert isinstance(closure[lane]["no_action_reason"], str)
        assert closure[lane]["no_action_reason"]


def test_top_level_closure_fallback_is_an_explicit_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        lane_productivity,
        "closure_snapshot",
        lambda _since: (_ for _ in ()).throw(RuntimeError("collector crashed")),
    )
    monkeypatch.setattr(sys, "argv", ["lane_productivity.py", "--since", "100", "--closure-json"])

    assert lane_productivity.main() == 0
    output = json.loads(capsys.readouterr().out)
    assert all(row["action_kind"] == "error" for row in output.values())
    assert all(row["status"] == "error" for row in output.values())
