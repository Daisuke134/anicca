"""A stuck delivery_unknown row must come back to life exactly once policy allows.

Run: python3 -m pytest skills/earn/gig/tests/test_telegram_redrive.py
"""
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from telegram_outbox import TelegramOutbox  # noqa: E402


def _state(outbox: TelegramOutbox, report_id: int) -> sqlite3.Row:
    with closing(outbox._connect()) as connection:
        return outbox._row(connection, report_id)


def _make_unknown(outbox: TelegramOutbox, *, event_key: str, created_at: int) -> int:
    row = outbox.enqueue(
        event_key=event_key, kind="pass", message="m", created_at=created_at,
    )
    report_id = int(row["report_id"])
    claimed = outbox.claim(owner="o", now=created_at, lease_seconds=60, report_id=report_id)
    started = outbox.mark_send_started(
        report_id, owner="o", fencing_token=int(claimed["fencing_token"]), now=created_at,
    )
    outbox.mark_delivery_unknown(
        report_id, owner="o", fencing_token=int(started["fencing_token"]),
        error_class="RuntimeError", now=created_at,
    )
    return report_id


def test_stale_row_under_attempt_cap_becomes_claimable_again(tmp_path):
    outbox = TelegramOutbox(tmp_path / "outbox.sqlite3")
    report_id = _make_unknown(outbox, event_key="k1", created_at=1000)
    moved = outbox.redrive_unresolved(now=1000 + 600, older_than_seconds=600, max_attempts=3)
    assert moved == 1
    row = _state(outbox, report_id)
    assert row["state"] == "pending"
    assert row["owner"] is None
    assert row["lease_until"] == 0
    assert row["error_class"] is None


def test_recent_row_is_left_alone(tmp_path):
    outbox = TelegramOutbox(tmp_path / "outbox.sqlite3")
    report_id = _make_unknown(outbox, event_key="k1", created_at=1000)
    moved = outbox.redrive_unresolved(now=1000 + 60, older_than_seconds=600, max_attempts=3)
    assert moved == 0
    row = _state(outbox, report_id)
    assert row["state"] == "delivery_unknown"


def test_row_at_attempt_cap_is_left_alone(tmp_path):
    outbox = TelegramOutbox(tmp_path / "outbox.sqlite3")
    report_id = _make_unknown(outbox, event_key="k1", created_at=1000)
    # One claim() already ran inside _make_unknown, so fencing_token is already 1.
    row = _state(outbox, report_id)
    assert int(row["fencing_token"]) == 1
    moved = outbox.redrive_unresolved(now=1000 + 600, older_than_seconds=600, max_attempts=1)
    assert moved == 0
    row = _state(outbox, report_id)
    assert row["state"] == "delivery_unknown"


def test_sent_row_is_never_touched(tmp_path):
    outbox = TelegramOutbox(tmp_path / "outbox.sqlite3")
    row = outbox.enqueue(event_key="k1", kind="pass", message="m", created_at=1000)
    report_id = int(row["report_id"])
    claimed = outbox.claim(owner="o", now=1000, lease_seconds=60, report_id=report_id)
    started = outbox.mark_send_started(
        report_id, owner="o", fencing_token=int(claimed["fencing_token"]), now=1000,
    )
    outbox.mark_sent(
        report_id, owner="o", fencing_token=int(started["fencing_token"]),
        message_id="123", now=1000,
    )
    moved = outbox.redrive_unresolved(now=1000 + 600, older_than_seconds=600, max_attempts=3)
    assert moved == 0
    row = _state(outbox, report_id)
    assert row["state"] == "sent"


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))


def test_a_report_too_old_to_be_news_is_left_where_it_died(tmp_path):
    """The first live run reopened 390 rows and queued hours of stale noop lines.

    A health report is only worth resending while it still describes now.
    """
    outbox = TelegramOutbox(tmp_path / "outbox.sqlite3")
    report_id = _make_unknown(outbox, event_key="ancient", created_at=1000)
    moved = outbox.redrive_unresolved(
        now=1000 + 86400, older_than_seconds=600, max_attempts=3, newer_than_seconds=3600,
    )
    assert moved == 0
    assert _state(outbox, report_id)["state"] == "delivery_unknown"
