from __future__ import annotations

import os
import sqlite3
import uuid
from pathlib import Path


class DeliveryUncertain(RuntimeError):
    pass


class Outbox:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.connection = sqlite3.connect(path, isolation_level=None)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS outbox (
              event_key TEXT PRIMARY KEY,
              payload TEXT NOT NULL,
              status TEXT NOT NULL,
              fence TEXT,
              telegram_message_id TEXT
            )
            """
        )
        os.chmod(path, 0o600)

    def close(self) -> None:
        self.connection.close()

    def enqueue(self, event_key: str, payload: str) -> str:
        self.connection.execute(
            "INSERT OR IGNORE INTO outbox(event_key,payload,status) VALUES(?,?,'pending')",
            (event_key, payload),
        )
        return event_key

    def claim(self, event_key: str) -> str:
        row = self.connection.execute(
            "SELECT status FROM outbox WHERE event_key=?", (event_key,)
        ).fetchone()
        if row is None:
            raise KeyError(event_key)
        if row[0] == "send_started":
            raise DeliveryUncertain("delivery outcome is unknown; blind retry forbidden")
        if row[0] != "pending":
            raise DeliveryUncertain(f"outbox is not claimable: {row[0]}")
        fence = uuid.uuid4().hex
        self.connection.execute(
            "UPDATE outbox SET status='claimed',fence=? WHERE event_key=? AND status='pending'",
            (fence, event_key),
        )
        return fence

    def mark_send_started(self, event_key: str, fence: str) -> None:
        changed = self.connection.execute(
            """
            UPDATE outbox SET status='send_started'
            WHERE event_key=? AND fence=? AND status='claimed'
            """,
            (event_key, fence),
        ).rowcount
        if changed != 1:
            raise DeliveryUncertain("outbox fence mismatch")

    def mark_sent(self, event_key: str, fence: str, message_id: str) -> None:
        changed = self.connection.execute(
            """
            UPDATE outbox SET status='sent',telegram_message_id=?
            WHERE event_key=? AND fence=? AND status='send_started'
            """,
            (message_id, event_key, fence),
        ).rowcount
        if changed != 1:
            raise DeliveryUncertain("outbox fence mismatch")

    def payload(self, event_key: str) -> str:
        row = self.connection.execute(
            "SELECT payload FROM outbox WHERE event_key=?", (event_key,)
        ).fetchone()
        if row is None:
            raise KeyError(event_key)
        return str(row[0])

    def status(self, event_key: str) -> dict[str, str | None]:
        row = self.connection.execute(
            "SELECT status,telegram_message_id FROM outbox WHERE event_key=?",
            (event_key,),
        ).fetchone()
        if row is None:
            raise KeyError(event_key)
        return {"status": str(row[0]), "message_id": row[1]}
