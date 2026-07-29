#!/usr/bin/env python3
"""Durable at-most-once Telegram report outbox."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator


class TelegramOutboxError(RuntimeError):
    pass


SCHEMA = """
CREATE TABLE IF NOT EXISTS telegram_reports (
    report_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_key TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL,
    message TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('pending','claimed','send_started','sent','delivery_unknown')),
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    owner TEXT,
    fencing_token INTEGER NOT NULL DEFAULT 0,
    lease_until INTEGER NOT NULL DEFAULT 0,
    send_started_at INTEGER,
    message_id TEXT,
    error_class TEXT
);
CREATE INDEX IF NOT EXISTS telegram_reports_state_idx
ON telegram_reports(state,created_at,report_id);
"""


class TelegramOutbox:
    def __init__(self, database: Path):
        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            connection.executescript(SCHEMA)
        self.database.chmod(0o600)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    @contextmanager
    def _write(self) -> Iterator[sqlite3.Connection]:
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
            except BaseException:
                connection.rollback()
                raise
            else:
                connection.commit()

    @staticmethod
    def _text(name: str, value: Any, maximum: int) -> str:
        text = str(value or "").strip()
        if not text or len(text) > maximum or "\x00" in text:
            raise ValueError(f"invalid {name}")
        return text

    @staticmethod
    def _integer(name: str, value: Any, *, positive: bool = False) -> int:
        if isinstance(value, bool):
            raise ValueError(f"invalid {name}")
        try:
            number = int(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"invalid {name}") from error
        if number < 0 or (positive and number <= 0):
            raise ValueError(f"invalid {name}")
        return number

    @staticmethod
    def _row(connection: sqlite3.Connection, report_id: int) -> sqlite3.Row:
        row = connection.execute(
            "SELECT * FROM telegram_reports WHERE report_id=?", (report_id,)
        ).fetchone()
        if row is None:
            raise TelegramOutboxError("unknown report")
        return row

    def enqueue(
        self, *, event_key: str, kind: str, message: str, created_at: int
    ) -> dict[str, Any]:
        event_key = self._text("event_key", event_key, 300)
        kind = self._text("kind", kind, 80)
        message = self._text("message", message, 4096)
        created_at = self._integer("created_at", created_at)
        with self._write() as connection:
            existing = connection.execute(
                "SELECT * FROM telegram_reports WHERE event_key=?", (event_key,)
            ).fetchone()
            if existing is not None:
                if existing["kind"] != kind or existing["message"] != message:
                    raise TelegramOutboxError("event payload mismatch")
                return dict(existing)
            cursor = connection.execute(
                """INSERT INTO telegram_reports
                   (event_key,kind,message,state,created_at,updated_at)
                   VALUES(?,?,?,'pending',?,?)""",
                (event_key, kind, message, created_at, created_at),
            )
            return dict(self._row(connection, int(cursor.lastrowid)))

    def claim(self, *, owner: str, now: int, lease_seconds: int) -> dict[str, Any] | None:
        owner = self._text("owner", owner, 200)
        now = self._integer("now", now)
        lease_seconds = self._integer("lease_seconds", lease_seconds, positive=True)
        with self._write() as connection:
            row = connection.execute(
                """SELECT * FROM telegram_reports
                   WHERE state='pending' OR (state='claimed' AND lease_until<=?)
                   ORDER BY created_at,report_id LIMIT 1""",
                (now,),
            ).fetchone()
            if row is None:
                return None
            token = int(row["fencing_token"]) + 1
            connection.execute(
                """UPDATE telegram_reports
                   SET state='claimed',owner=?,fencing_token=?,lease_until=?,updated_at=?
                   WHERE report_id=?""",
                (owner, token, now + lease_seconds, now, row["report_id"]),
            )
            return dict(self._row(connection, int(row["report_id"])))

    def _fenced(
        self,
        connection: sqlite3.Connection,
        report_id: int,
        *,
        owner: str,
        fencing_token: int,
        state: str,
        now: int | None = None,
    ) -> sqlite3.Row:
        row = self._row(connection, report_id)
        valid = (
            row["state"] == state
            and row["owner"] == owner
            and int(row["fencing_token"]) == int(fencing_token)
        )
        if now is not None:
            valid = valid and int(row["lease_until"]) > now
        if not valid:
            raise TelegramOutboxError("stale Telegram report fence")
        return row

    def mark_send_started(
        self, report_id: int, *, owner: str, fencing_token: int, now: int
    ) -> dict[str, Any]:
        report_id = self._integer("report_id", report_id, positive=True)
        fencing_token = self._integer("fencing_token", fencing_token, positive=True)
        now = self._integer("now", now)
        with self._write() as connection:
            row = self._fenced(
                connection, report_id, owner=owner, fencing_token=fencing_token,
                state="claimed", now=now,
            )
            if now < int(row["updated_at"]):
                raise TelegramOutboxError("non-monotonic send start")
            connection.execute(
                """UPDATE telegram_reports
                   SET state='send_started',send_started_at=?,updated_at=?
                   WHERE report_id=?""",
                (now, now, report_id),
            )
            return dict(self._row(connection, report_id))

    def mark_sent(
        self,
        report_id: int,
        *,
        owner: str,
        fencing_token: int,
        message_id: str,
        now: int,
    ) -> dict[str, Any]:
        report_id = self._integer("report_id", report_id, positive=True)
        message_id = self._text("message_id", message_id, 300)
        now = self._integer("now", now)
        with self._write() as connection:
            row = self._fenced(
                connection, report_id, owner=owner, fencing_token=fencing_token,
                state="send_started",
            )
            if now < int(row["send_started_at"]):
                raise TelegramOutboxError("non-monotonic Telegram ACK")
            connection.execute(
                """UPDATE telegram_reports
                   SET state='sent',message_id=?,owner=NULL,lease_until=0,updated_at=?
                   WHERE report_id=?""",
                (message_id, now, report_id),
            )
            return dict(self._row(connection, report_id))

    def mark_delivery_unknown(
        self,
        report_id: int,
        *,
        owner: str,
        fencing_token: int,
        error_class: str,
        now: int,
    ) -> dict[str, Any]:
        report_id = self._integer("report_id", report_id, positive=True)
        error_class = self._text("error_class", error_class, 120)
        now = self._integer("now", now)
        with self._write() as connection:
            row = self._fenced(
                connection, report_id, owner=owner, fencing_token=fencing_token,
                state="send_started",
            )
            if now < int(row["send_started_at"]):
                raise TelegramOutboxError("non-monotonic Telegram failure")
            connection.execute(
                """UPDATE telegram_reports
                   SET state='delivery_unknown',error_class=?,owner=NULL,lease_until=0,updated_at=?
                   WHERE report_id=?""",
                (error_class, now, report_id),
            )
            return dict(self._row(connection, report_id))

    def recover_expired(self, *, now: int) -> int:
        """Quarantine provider calls whose executor disappeared; never resend them."""
        now = self._integer("now", now)
        with self._write() as connection:
            cursor = connection.execute(
                """UPDATE telegram_reports
                   SET state='delivery_unknown',error_class='executor_lost_after_send_start',
                       owner=NULL,lease_until=0,updated_at=?
                   WHERE state='send_started' AND lease_until<=?""",
                (now, now),
            )
            return int(cursor.rowcount)

    def reconcile_receipts(
        self,
        *,
        receipt_dir: Path,
        target: str,
        now: int,
    ) -> dict[str, int]:
        """Confirm provider-ACKed unknown sends from event-bound durable receipts."""
        receipt_dir = Path(receipt_dir)
        target = self._text("target", target, 200)
        now = self._integer("now", now)
        if not receipt_dir.is_dir():
            return {"reconciled": 0, "invalid": 0}
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM telegram_reports WHERE state='delivery_unknown'"
            ).fetchall()
        reconciled = 0
        invalid = 0
        for row in rows:
            event_key = str(row["event_key"])
            receipt_name = hashlib.sha256(event_key.encode("utf-8")).hexdigest()
            receipt_path = receipt_dir / f"{receipt_name}.json"
            if not receipt_path.is_file():
                continue
            try:
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                message_hash = hashlib.sha256(
                    str(row["message"]).encode("utf-8")
                ).hexdigest()
                ack_ms = int(receipt["provider_acked_at_epoch_ms"])
                message_id = self._text(
                    "message_id", receipt.get("message_id"), 300
                )
                valid = (
                    receipt.get("version") == 1
                    and receipt.get("event_key") == event_key
                    and receipt.get("target") == target
                    and receipt.get("message_sha256") == message_hash
                    and ack_ms >= int(row["send_started_at"] or 0) * 1000
                    and ack_ms <= now * 1000
                )
            except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
                valid = False
                message_id = ""
            if not valid:
                invalid += 1
                continue
            with self._write() as connection:
                current = self._row(connection, int(row["report_id"]))
                if current["state"] != "delivery_unknown":
                    continue
                connection.execute(
                    """UPDATE telegram_reports
                       SET state='sent',message_id=?,error_class='reconciled_provider_receipt',
                           owner=NULL,lease_until=0,updated_at=?
                       WHERE report_id=? AND state='delivery_unknown'""",
                    (message_id, now, row["report_id"]),
                )
            reconciled += 1
        return {"reconciled": reconciled, "invalid": invalid}

    def counts(self) -> dict[str, int]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT state,COUNT(*) AS count FROM telegram_reports GROUP BY state"
            ).fetchall()
            return {str(row["state"]): int(row["count"]) for row in rows}


def dispatch_one(
    outbox: TelegramOutbox,
    *,
    owner: str,
    now: Callable[[], int],
    transport: Callable[[str], str],
    lease_seconds: int = 60,
) -> dict[str, Any]:
    action = outbox.claim(owner=owner, now=now(), lease_seconds=lease_seconds)
    if action is None:
        return {"status": "queue_empty", "message_id": None}
    started = outbox.mark_send_started(
        int(action["report_id"]),
        owner=owner,
        fencing_token=int(action["fencing_token"]),
        now=now(),
    )
    try:
        send_report = getattr(transport, "send_report", None)
        if callable(send_report):
            message_id = send_report(
                str(started["message"]),
                event_key=str(started["event_key"]),
            )
        else:
            message_id = transport(str(started["message"]))
        sent = outbox.mark_sent(
            int(started["report_id"]),
            owner=owner,
            fencing_token=int(started["fencing_token"]),
            message_id=message_id,
            now=now(),
        )
        return {"status": "sent", "message_id": str(sent["message_id"])}
    except Exception as error:
        unknown = outbox.mark_delivery_unknown(
            int(started["report_id"]),
            owner=owner,
            fencing_token=int(started["fencing_token"]),
            error_class=type(error).__name__,
            now=now(),
        )
        return {"status": "delivery_unknown", "message_id": unknown["message_id"]}
