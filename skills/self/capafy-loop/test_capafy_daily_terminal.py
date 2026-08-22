from pathlib import Path

import json

import pytest

from capafy_daily_terminal import append_event, classify_result, streak_status


def test_streak_requires_started_and_healthy_terminal_for_each_day(tmp_path: Path) -> None:
    ledger = tmp_path / "terminals.jsonl"
    append_event(ledger, "a", "started", None, None, "2026-08-20T00:00:00Z")
    append_event(ledger, "a", "terminal", 0, "CAP_FULL", "2026-08-20T00:01:00Z")
    append_event(ledger, "b", "started", None, None, "2026-08-21T00:00:00Z")
    append_event(ledger, "b", "terminal", 0, "CAP_FULL", "2026-08-21T00:01:00Z")
    append_event(ledger, "c", "started", None, None, "2026-08-22T00:00:00Z")
    append_event(ledger, "c", "terminal", 0, "CAP_FULL", "2026-08-22T00:01:00Z")

    assert streak_status(ledger, "2026-08-22")["consecutive_healthy_days"] == 3


def test_failure_or_missing_terminal_breaks_streak(tmp_path: Path) -> None:
    ledger = tmp_path / "terminals.jsonl"
    append_event(ledger, "a", "started", None, None, "2026-08-21T00:00:00Z")
    append_event(ledger, "a", "terminal", 1, "SERVER_UNREADABLE", "2026-08-21T00:01:00Z")
    append_event(ledger, "b", "started", None, None, "2026-08-22T00:00:00Z")
    append_event(ledger, "b", "terminal", 0, "CAP_FULL", "2026-08-22T00:01:00Z")

    assert streak_status(ledger, "2026-08-22")["consecutive_healthy_days"] == 1

    append_event(ledger, "c", "started", None, None, "2026-08-22T02:00:00Z")
    assert streak_status(ledger, "2026-08-22")["consecutive_healthy_days"] == 0


@pytest.mark.parametrize(("status", "expected_rc"), (("success", 0), ("no_op", 0), ("failure", 1)))
def test_classify_result_maps_status_to_terminal_rc(tmp_path: Path, status: str, expected_rc: int) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    result = evidence / "attempt.result.json"
    result.write_text(json.dumps({"status": status, "evidence": ["official readback"]}), encoding="utf-8")
    summary = evidence / "summary.json"
    summary.write_text(json.dumps({"result_path": str(result)}), encoding="utf-8")

    rc, value = classify_result(summary)

    assert rc == expected_rc
    assert value["status"] == status


@pytest.mark.parametrize(
    "summary_builder",
    (
        lambda root: root / "missing-summary.json",
        lambda root: _write_summary(root, "not-json", None),
        lambda root: _write_summary(root, json.dumps({"result_path": str(root.parent / "outside.json")}), None),
        lambda root: _write_summary(root, json.dumps({"result_path": str(root / "result.json")}), {"status": "unknown", "evidence": ["x"]}),
        lambda root: _write_nested_summary(root),
    ),
)
def test_classify_result_invalid_or_escaped_is_rc2(tmp_path: Path, summary_builder) -> None:
    summary = summary_builder(tmp_path)
    rc, value = classify_result(summary)
    assert rc == 2
    assert value["status"] == "invalid"


def _write_summary(root: Path, summary_text: str, result: dict | None) -> Path:
    summary = root / "summary.json"
    summary.write_text(summary_text, encoding="utf-8")
    if result is not None:
        (root / "result.json").write_text(json.dumps(result), encoding="utf-8")
    return summary


def _write_nested_summary(root: Path) -> Path:
    nested = root / "nested"
    nested.mkdir()
    (nested / "result.json").write_text(json.dumps({"status": "success", "evidence": ["x"]}), encoding="utf-8")
    return _write_summary(root, json.dumps({"result_path": str(nested / "result.json")}), None)
