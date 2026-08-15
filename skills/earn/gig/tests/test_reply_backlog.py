from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path


# Dais, 2026-08-05: "the person who is messaging us ... why is the loop not replying to this?"
#
# Seven buyers were sitting in connector_actions at state='pending', the oldest since
# 2026-08-01, and six more at 'blocked' since 2026-07-23. The reply lane ran every pass and
# reported success, and it never touched any of them, because the pass gates the lane on
#
#     [ "$REPLY_ITEM_COUNT" -gt 0 ] || return 0
#
# and REPLY_ITEM_COUNT counts only the inquiries found in THIS pass's snapshot. An hour in
# which no new message arrives therefore skips the lane entirely -- including the backlog it
# already owes replies to. reply_lane can already drain pending_actions(); nothing ever asked
# it to.

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "reply_backlog.py"


def load_module():
    scripts_dir = str(MODULE_PATH.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("reply_backlog", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_outbox(path: Path, rows: list[tuple[str, str]]) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            """CREATE TABLE connector_actions (
                   action_id INTEGER PRIMARY KEY AUTOINCREMENT,
                   platform TEXT NOT NULL,
                   thread_id TEXT NOT NULL,
                   state TEXT NOT NULL,
                   created_at INTEGER NOT NULL DEFAULT 0)"""
        )
        connection.executemany(
            "INSERT INTO connector_actions(platform,thread_id,state) VALUES('coconala',?,?)",
            rows,
        )


def test_the_seven_waiting_buyers_are_counted(tmp_path) -> None:
    database = tmp_path / "connector-outbox.sqlite3"
    make_outbox(database, [(str(i), "pending") for i in range(7)])
    assert load_module().pending_count(database) == 7


def test_replied_threads_are_not_a_backlog(tmp_path) -> None:
    database = tmp_path / "connector-outbox.sqlite3"
    make_outbox(database, [("1", "replied"), ("2", "replied"), ("3", "pending")])
    assert load_module().pending_count(database) == 1


def test_a_missing_database_is_zero_not_a_crash(tmp_path) -> None:
    # The gate runs before the lane on every pass. A backlog counter that raises would take
    # the reply lane down for a reason that has nothing to do with any buyer.
    assert load_module().pending_count(tmp_path / "absent.sqlite3") == 0


def test_a_database_without_the_table_is_zero_not_a_crash(tmp_path) -> None:
    database = tmp_path / "connector-outbox.sqlite3"
    sqlite3.connect(database).close()
    assert load_module().pending_count(database) == 0
