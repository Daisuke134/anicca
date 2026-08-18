#!/usr/bin/env python3
"""At-most-once ledger for one outgoing message per inbound retainer event.

Sibling of retainer_booking.py, same discipline -- durable intent, then execute,
then authoritative readback, then ledger -- for the other irreversible thing this
lane does: writing to a real client.

Why the identity is the INBOUND event and not our outgoing text
---------------------------------------------------------------
connector_outbox keys a reply to its intent revision and proves delivery by finding
our body hash in the thread, which requires the retry to send byte-identical text.
That works there because the composed body survives inside one process.  Here a
crash can land between "compose" and "send", and the composed text is deliberately
NOT persisted (the reply lane's rule: hashes, never customer prose).  A retry would
therefore have to re-compose, produce different words, and a text-keyed ledger would
either refuse it forever or lose the at-most-once property.

So the durable identity is "the client message we owe an answer to", and the
authoritative question asked of the platform is "does a message from us exist that
is newer than theirs?".  That is decidable from a readback with no stored prose, it
is exactly the question `_next_action` already answers off the thread, and it stays
correct even if the retry's wording differs.

States:
    intent       -> we owe this event an answer; sending is allowed
    send_started -> a send was authorized; sending is NOT allowed again
    sent         -> the thread shows our answer; terminal
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


class MessageError(RuntimeError):
    """A message transition that must never be papered over."""


class ImmutableMessage(MessageError):
    """This inbound event is already bound to a different answer."""


class InvalidMessageTransition(MessageError):
    """The ledger is not in a state where this step is legal."""


STATE_INTENT = "intent"
STATE_SEND_STARTED = "send_started"
STATE_SENT = "sent"

SCHEMA = """
CREATE TABLE IF NOT EXISTS retainer_messages (
    message_key TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    event_key TEXT NOT NULL,
    inbound_sent_at TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('intent','send_started','sent')),
    attempt_hash TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    send_started_at INTEGER,
    sent_at INTEGER,
    seller_sent_at TEXT,
    duplicate_detected INTEGER NOT NULL DEFAULT 0,
    reported_at INTEGER
);
CREATE UNIQUE INDEX IF NOT EXISTS retainer_messages_event
ON retainer_messages(thread_id, event_key);
"""


def message_key(thread_id: str, event_key: str) -> str:
    return hashlib.sha256(f"{thread_id}:{event_key}".encode("utf-8")).hexdigest()[:32]


def body_hash(body: str) -> str:
    return hashlib.sha256(str(body).encode("utf-8")).hexdigest()


class MessageLedger:
    """Durable, crash-safe state for one answer per inbound retainer message."""

    def __init__(self, database: Path | str):
        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database, isolation_level=None, timeout=30)
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript(SCHEMA)
        finally:
            connection.close()
        try:
            self.database.chmod(0o600)
        except OSError:
            pass

    @contextmanager
    def _write(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database, isolation_level=None, timeout=30)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.execute("COMMIT")
        except BaseException:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        finally:
            connection.close()

    def _row(self, connection: sqlite3.Connection, key: str) -> sqlite3.Row:
        row = connection.execute(
            "SELECT * FROM retainer_messages WHERE message_key=?", (key,)
        ).fetchone()
        if row is None:
            raise InvalidMessageTransition("unknown message")
        return row

    def get(self, key: str) -> dict[str, Any] | None:
        with self._write() as connection:
            row = connection.execute(
                "SELECT * FROM retainer_messages WHERE message_key=?", (key,)
            ).fetchone()
            return dict(row) if row is not None else None

    def open_intent(
        self, *, thread_id: str, event_key: str, inbound_sent_at: str, now: int
    ) -> dict[str, Any]:
        """Record that this inbound message is owed exactly one answer."""
        if not str(event_key).strip():
            raise ValueError("event_key is required")
        if not str(inbound_sent_at).strip():
            raise ValueError("inbound_sent_at is required")
        key = message_key(str(thread_id), str(event_key))
        with self._write() as connection:
            existing = connection.execute(
                "SELECT * FROM retainer_messages WHERE message_key=?", (key,)
            ).fetchone()
            if existing is not None:
                if str(existing["inbound_sent_at"]) != str(inbound_sent_at):
                    raise ImmutableMessage(
                        "this event is already bound to another inbound timestamp"
                    )
                return dict(existing)
            connection.execute(
                """INSERT INTO retainer_messages
                   (message_key,thread_id,event_key,inbound_sent_at,state,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?)""",
                (
                    key, str(thread_id), str(event_key), str(inbound_sent_at),
                    STATE_INTENT, int(now), int(now),
                ),
            )
            return dict(self._row(connection, key))

    def may_send(self, key: str) -> bool:
        """Only a row that has never authorized a send may send."""
        row = self.get(key)
        return row is not None and row["state"] == STATE_INTENT

    def mark_send_started(
        self, key: str, *, attempt_hash: str, now: int
    ) -> dict[str, Any]:
        """Authorize exactly one irreversible send attempt."""
        if len(str(attempt_hash)) != 64:
            raise ValueError("attempt_hash must be a sha256 hex digest")
        with self._write() as connection:
            row = self._row(connection, key)
            if row["state"] != STATE_INTENT:
                raise InvalidMessageTransition(
                    f"cannot start a send from state {row['state']}"
                )
            connection.execute(
                """UPDATE retainer_messages
                   SET state=?,attempt_hash=?,send_started_at=?,updated_at=?
                   WHERE message_key=? AND state=?""",
                (
                    STATE_SEND_STARTED, str(attempt_hash), int(now), int(now),
                    key, STATE_INTENT,
                ),
            )
            return dict(self._row(connection, key))

    def reconcile(
        self, key: str, *, observation: dict[str, Any], now: int
    ) -> dict[str, Any]:
        """Resolve an in-flight send from an authoritative thread reading.

        ``answered`` must mean "a message from us exists that is newer than the
        client message this row owes an answer to" -- read off the live thread, never
        inferred from our own return value.
        """
        if not isinstance(observation, dict):
            raise ValueError("observation must be a mapping")
        answered = observation.get("answered")
        if type(answered) is not bool:
            raise ValueError("observation lacks a boolean answered")
        with self._write() as connection:
            row = self._row(connection, key)
            if str(observation.get("thread_id") or "") != row["thread_id"]:
                raise ValueError("observation identifies another thread")
            if row["state"] == STATE_SENT:
                return dict(row)
            if row["state"] != STATE_SEND_STARTED:
                raise InvalidMessageTransition("no send is in flight")
            if not answered:
                connection.execute(
                    """UPDATE retainer_messages
                       SET state=?,send_started_at=NULL,updated_at=?
                       WHERE message_key=? AND state=?""",
                    (STATE_INTENT, int(now), key, STATE_SEND_STARTED),
                )
                return dict(self._row(connection, key))
            duplicate = 1 if int(observation.get("answer_count") or 1) > 1 else 0
            connection.execute(
                """UPDATE retainer_messages
                   SET state=?,sent_at=?,seller_sent_at=?,duplicate_detected=?,updated_at=?
                   WHERE message_key=? AND state=?""",
                (
                    STATE_SENT, int(now),
                    str(observation.get("seller_sent_at") or "") or None,
                    duplicate, int(now), key, STATE_SEND_STARTED,
                ),
            )
            return dict(self._row(connection, key))

    def adopt_existing_answer(
        self, key: str, *, observation: dict[str, Any], now: int
    ) -> dict[str, Any]:
        """Close a row whose answer already exists on the thread before we sent.

        This is what stops a second pass from answering a message a previous pass
        already answered but never got to record -- or that Dais answered by hand.
        """
        if observation.get("answered") is not True:
            raise ValueError("nothing to adopt")
        with self._write() as connection:
            row = self._row(connection, key)
            if str(observation.get("thread_id") or "") != row["thread_id"]:
                raise ValueError("observation identifies another thread")
            if row["state"] == STATE_SENT:
                return dict(row)
            if row["state"] != STATE_INTENT:
                raise InvalidMessageTransition("a send is already in flight")
            connection.execute(
                """UPDATE retainer_messages
                   SET state=?,sent_at=?,seller_sent_at=?,updated_at=?
                   WHERE message_key=? AND state=?""",
                (
                    STATE_SENT, int(now),
                    str(observation.get("seller_sent_at") or "") or None,
                    int(now), key, STATE_INTENT,
                ),
            )
            return dict(self._row(connection, key))

    def reportable(self, key: str) -> bool:
        row = self.get(key)
        return (
            row is not None
            and row["state"] == STATE_SENT
            and row["reported_at"] is None
        )

    def mark_reported(self, key: str, *, now: int) -> dict[str, Any]:
        with self._write() as connection:
            self._row(connection, key)
            connection.execute(
                """UPDATE retainer_messages SET reported_at=?,updated_at=?
                   WHERE message_key=? AND reported_at IS NULL""",
                (int(now), int(now), key),
            )
            return dict(self._row(connection, key))


def default_database() -> Path:
    return Path(
        os.environ.get(
            "GIG_RETAINER_MESSAGE_DB",
            str(Path.home() / "gig" / "retainer-messages.sqlite3"),
        )
    )


def summarize(database: Path | str) -> str:
    """Small helper for operators reading the ledger from a shell."""
    ledger = MessageLedger(database)
    with ledger._write() as connection:  # noqa: SLF001 - same module
        rows = [dict(row) for row in connection.execute(
            "SELECT thread_id,state,seller_sent_at,reported_at FROM retainer_messages"
        )]
    return json.dumps(rows, ensure_ascii=False, indent=2)
