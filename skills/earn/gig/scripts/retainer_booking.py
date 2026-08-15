#!/usr/bin/env python3
"""At-most-once ledger for confirming an interview slot on Coconala.

Confirming a slot is irreversible and externally visible: the platform tells the
client a time is agreed and the modal never reappears.  It therefore gets the same
discipline every other side effect in this loop gets -- durable intent, then
execute, then authoritative readback, then ledger -- rather than a best-effort
click that a crash could repeat.

The shape mirrors ConnectorOutbox: one row per (thread, offer), an immutable
decision once written, an explicit confirm_started state that a recovering process
refuses to click through blind, and a reconcile step that only moves the row on
evidence read back off the live thread.  The unique key is the offer, not the pass,
so replaying a whole pass converges instead of double-booking.

States:
    intent          -> a slot was chosen; clicking is allowed
    confirm_started -> a click was authorized; clicking is NOT allowed again
    confirmed       -> the platform shows the interview as agreed; terminal
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


class BookingError(RuntimeError):
    """A booking transition that must never be papered over."""


class ImmutableBooking(BookingError):
    """A decision or calendar entry already exists and differs from this one."""


class InvalidBookingTransition(BookingError):
    """The ledger is not in a state where this step is legal."""


STATE_INTENT = "intent"
STATE_CONFIRM_STARTED = "confirm_started"
STATE_CONFIRMED = "confirmed"

SCHEMA = """
CREATE TABLE IF NOT EXISTS retainer_bookings (
    booking_key TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    offer_hash TEXT NOT NULL CHECK (length(offer_hash) = 64),
    decision_json TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('intent','confirm_started','confirmed')),
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    confirm_started_at INTEGER,
    confirmed_at INTEGER,
    confirmed_start TEXT,
    calendar_event_id TEXT,
    reported_at INTEGER
);
CREATE UNIQUE INDEX IF NOT EXISTS retainer_bookings_offer
ON retainer_bookings(thread_id, offer_hash);
-- One confirmed interview per thread, enforced by the database and not by a
-- caller remembering to check first.
CREATE UNIQUE INDEX IF NOT EXISTS retainer_bookings_one_confirmed
ON retainer_bookings(thread_id) WHERE state = 'confirmed';
"""


def offer_hash(offer: dict[str, Any]) -> str:
    """Stable identity for one offer, so a re-read of the same offer is one row."""
    payload = json.dumps(offer, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def booking_key(thread_id: str, digest: str) -> str:
    return hashlib.sha256(f"{thread_id}:{digest}".encode("utf-8")).hexdigest()[:32]


def _canonical_decision(decision: dict[str, Any]) -> str:
    if not isinstance(decision, dict):
        raise ValueError("decision must be a mapping")
    if decision.get("decision") not in {"accept", "counter_propose"}:
        raise ValueError("unsupported booking decision")
    keep = {key: decision[key] for key in ("decision", "slot", "proposals") if key in decision}
    return json.dumps(keep, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class BookingLedger:
    """Durable, crash-safe state for interview confirmations."""

    def __init__(self, database: Path | str):
        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        # executescript() commits and closes any open transaction, so schema setup
        # runs on its own connection rather than inside _write()'s BEGIN IMMEDIATE.
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
            connection.execute("PRAGMA foreign_keys=ON")
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
            "SELECT * FROM retainer_bookings WHERE booking_key=?", (key,)
        ).fetchone()
        if row is None:
            raise InvalidBookingTransition("unknown booking")
        return row

    def get(self, key: str) -> dict[str, Any] | None:
        with self._write() as connection:
            row = connection.execute(
                "SELECT * FROM retainer_bookings WHERE booking_key=?", (key,)
            ).fetchone()
            return dict(row) if row is not None else None

    def open_intent(
        self,
        *,
        thread_id: str,
        offer_hash: str,
        decision: dict[str, Any],
        now: int,
    ) -> dict[str, Any]:
        """Record the chosen slot durably before anything irreversible happens.

        Replaying this with the same offer returns the existing row untouched --
        that is what makes a crashed pass safe to run again.  Replaying it with a
        DIFFERENT slot for the same offer is refused: the first decision is the one
        the platform may already have seen.
        """
        digest = str(offer_hash)
        if len(digest) != 64:
            raise ValueError("offer_hash must be a sha256 hex digest")
        key = booking_key(str(thread_id), digest)
        payload = _canonical_decision(decision)
        with self._write() as connection:
            existing = connection.execute(
                "SELECT * FROM retainer_bookings WHERE booking_key=?", (key,)
            ).fetchone()
            if existing is not None:
                if existing["decision_json"] != payload:
                    raise ImmutableBooking(
                        "a different decision is already durable for this offer"
                    )
                return dict(existing)
            connection.execute(
                """INSERT INTO retainer_bookings
                   (booking_key,thread_id,offer_hash,decision_json,state,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?)""",
                (key, str(thread_id), digest, payload, STATE_INTENT, int(now), int(now)),
            )
            return dict(self._row(connection, key))

    def may_confirm(self, key: str) -> bool:
        """Only a row that has never authorized a click may click."""
        row = self.get(key)
        return row is not None and row["state"] == STATE_INTENT

    def mark_confirm_started(self, key: str, *, now: int) -> dict[str, Any]:
        """Authorize exactly one irreversible confirmation attempt."""
        with self._write() as connection:
            row = self._row(connection, key)
            if row["state"] != STATE_INTENT:
                raise InvalidBookingTransition(
                    f"cannot start confirmation from state {row['state']}"
                )
            connection.execute(
                """UPDATE retainer_bookings
                   SET state=?,confirm_started_at=?,updated_at=?
                   WHERE booking_key=? AND state=?""",
                (STATE_CONFIRM_STARTED, int(now), int(now), key, STATE_INTENT),
            )
            return dict(self._row(connection, key))

    def reconcile(
        self, key: str, *, observation: dict[str, Any], now: int
    ) -> dict[str, Any]:
        """Resolve an in-flight confirmation from an authoritative thread reading.

        Confirmed on the platform -> terminal, and never clicked again.
        Not confirmed -> back to intent, so the SAME slot is retried rather than a
        new one being chosen, which is what keeps the outcome single-valued.
        """
        if not isinstance(observation, dict):
            raise ValueError("observation must be a mapping")
        confirmed = observation.get("interview_confirmed")
        if type(confirmed) is not bool:
            raise ValueError("observation lacks a boolean interview_confirmed")
        with self._write() as connection:
            row = self._row(connection, key)
            if str(observation.get("thread_id") or "") != row["thread_id"]:
                raise ValueError("observation identifies another thread")
            if row["state"] == STATE_CONFIRMED:
                return dict(row)
            if row["state"] != STATE_CONFIRM_STARTED:
                raise InvalidBookingTransition("no confirmation is in flight")
            if not confirmed:
                connection.execute(
                    """UPDATE retainer_bookings
                       SET state=?,confirm_started_at=NULL,updated_at=?
                       WHERE booking_key=? AND state=?""",
                    (STATE_INTENT, int(now), key, STATE_CONFIRM_STARTED),
                )
                return dict(self._row(connection, key))
            connection.execute(
                """UPDATE retainer_bookings
                   SET state=?,confirmed_at=?,confirmed_start=?,updated_at=?
                   WHERE booking_key=? AND state=?""",
                (
                    STATE_CONFIRMED,
                    int(now),
                    str(observation.get("confirmed_start") or "") or None,
                    int(now),
                    key,
                    STATE_CONFIRM_STARTED,
                ),
            )
            return dict(self._row(connection, key))

    def adopt_existing_confirmation(
        self, key: str, *, observation: dict[str, Any], now: int
    ) -> dict[str, Any]:
        """Close a row whose interview the platform already shows as agreed.

        A row can sit at `intent` while the booking is real: a confirmation that the
        readback failed to recognise rolls the row back, and the next pass then reads
        the thread correctly. Without this, that row either strands (never calendared,
        never reported) or -- far worse -- is treated as still owed and clicked again.
        The platform saying "confirmed" is terminal regardless of what we recorded.
        """
        if observation.get("interview_confirmed") is not True:
            raise ValueError("nothing to adopt")
        with self._write() as connection:
            row = self._row(connection, key)
            if str(observation.get("thread_id") or "") != row["thread_id"]:
                raise ValueError("observation identifies another thread")
            if row["state"] == STATE_CONFIRMED:
                return dict(row)
            connection.execute(
                """UPDATE retainer_bookings
                   SET state=?,confirmed_at=?,confirmed_start=?,confirm_started_at=NULL,updated_at=?
                   WHERE booking_key=? AND state IN (?,?)""",
                (
                    STATE_CONFIRMED, int(now),
                    str(observation.get("confirmed_start") or "") or None,
                    int(now), key, STATE_INTENT, STATE_CONFIRM_STARTED,
                ),
            )
            return dict(self._row(connection, key))

    def needs_calendar_entry(self, key: str) -> bool:
        row = self.get(key)
        return (
            row is not None
            and row["state"] == STATE_CONFIRMED
            and row["calendar_event_id"] is None
        )

    def record_calendar_entry(
        self, key: str, *, event_id: str, now: int
    ) -> dict[str, Any]:
        """Bind the one calendar event for this booking; a second id is refused."""
        with self._write() as connection:
            row = self._row(connection, key)
            if row["state"] != STATE_CONFIRMED:
                raise InvalidBookingTransition(
                    "a calendar entry cannot precede a confirmed interview"
                )
            if row["calendar_event_id"] is not None:
                if row["calendar_event_id"] != str(event_id):
                    raise ImmutableBooking(
                        "a different calendar event is already bound to this booking"
                    )
                return dict(row)
            connection.execute(
                """UPDATE retainer_bookings
                   SET calendar_event_id=?,updated_at=?
                   WHERE booking_key=? AND calendar_event_id IS NULL""",
                (str(event_id), int(now), key),
            )
            return dict(self._row(connection, key))

    def reportable(self, key: str) -> bool:
        """Telegram hears about a booking only after it is real on both systems."""
        row = self.get(key)
        return (
            row is not None
            and row["state"] == STATE_CONFIRMED
            and row["calendar_event_id"] is not None
            and row["reported_at"] is None
        )

    def mark_reported(self, key: str, *, now: int) -> dict[str, Any]:
        with self._write() as connection:
            self._row(connection, key)
            connection.execute(
                """UPDATE retainer_bookings SET reported_at=?,updated_at=?
                   WHERE booking_key=? AND reported_at IS NULL""",
                (int(now), int(now), key),
            )
            return dict(self._row(connection, key))

    def confirmed_for_thread(self, thread_id: str) -> dict[str, Any] | None:
        with self._write() as connection:
            row = connection.execute(
                "SELECT * FROM retainer_bookings WHERE thread_id=? AND state=?",
                (str(thread_id), STATE_CONFIRMED),
            ).fetchone()
            return dict(row) if row is not None else None


def default_database() -> Path:
    return Path(
        os.environ.get(
            "GIG_RETAINER_BOOKING_DB",
            str(Path.home() / "gig" / "retainer-bookings.sqlite3"),
        )
    )
