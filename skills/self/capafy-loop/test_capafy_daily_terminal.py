from pathlib import Path

from capafy_daily_terminal import append_event, streak_status


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
