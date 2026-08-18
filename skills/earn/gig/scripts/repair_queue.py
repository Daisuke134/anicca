#!/usr/bin/env python3
"""Transactional, fenced incident queue for bounded Gig repairs."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS repair_queue (
    incident_id INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint TEXT NOT NULL,
    repair_class TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'queued',
    evidence_json TEXT NOT NULL,
    verification_json TEXT,
    occurrence_count INTEGER NOT NULL DEFAULT 1,
    first_detected_at INTEGER NOT NULL,
    last_detected_at INTEGER NOT NULL,
    owner TEXT,
    fencing_token INTEGER NOT NULL DEFAULT 0,
    lease_until INTEGER NOT NULL DEFAULT 0,
    recovered_at INTEGER,
    blocked_at INTEGER,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    next_attempt_at INTEGER NOT NULL DEFAULT 0,
    last_action_json TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS repair_queue_one_open_fingerprint
ON repair_queue(fingerprint)
WHERE state IN ('queued', 'claimed', 'blocked');
"""


class LostLease(RuntimeError):
    """The repair worker no longer owns the incident fence."""


class RepairQueue:
    def __init__(self, database: Path | str):
        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(SCHEMA)
            self._migrate(connection)

    @staticmethod
    def _migrate(connection: sqlite3.Connection) -> None:
        columns = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(repair_queue)").fetchall()
        }
        migrations = {
            "blocked_at": "ALTER TABLE repair_queue ADD COLUMN blocked_at INTEGER",
            "attempt_count": (
                "ALTER TABLE repair_queue ADD COLUMN "
                "attempt_count INTEGER NOT NULL DEFAULT 0"
            ),
            "next_attempt_at": (
                "ALTER TABLE repair_queue ADD COLUMN "
                "next_attempt_at INTEGER NOT NULL DEFAULT 0"
            ),
            "last_action_json": (
                "ALTER TABLE repair_queue ADD COLUMN last_action_json TEXT"
            ),
        }
        for name, statement in migrations.items():
            if name not in columns:
                connection.execute(statement)
        connection.execute("DROP INDEX IF EXISTS repair_queue_one_open_fingerprint")
        connection.execute(
            """CREATE UNIQUE INDEX repair_queue_one_open_fingerprint
               ON repair_queue(fingerprint)
               WHERE state IN ('queued','claimed','blocked')"""
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=5, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        value = dict(row)
        value["evidence"] = json.loads(value.pop("evidence_json"))
        raw_verification = value.pop("verification_json")
        value["verification"] = (
            json.loads(raw_verification) if raw_verification is not None else None
        )
        raw_action = value.pop("last_action_json", None)
        value["last_action"] = (
            json.loads(raw_action) if raw_action is not None else None
        )
        return value

    def list_incidents(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM repair_queue ORDER BY incident_id"
            ).fetchall()
        return [self._row(row) for row in rows]

    def requeue_resolved_blocked(
        self,
        *,
        active_fingerprints: set[str],
        now: int,
    ) -> list[dict[str, Any]]:
        """Re-open blocked incidents only after their fingerprint disappears.

        The controller performs another fresh observation after claiming the
        requeued row, so absence here is not by itself recovery.
        """
        encoded = json.dumps(
            {
                "reason": "blocked_fingerprint_absent_recheck",
                "observed_at": int(now),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        requeued_ids: list[int] = []
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                "SELECT incident_id,fingerprint FROM repair_queue WHERE state='blocked'"
            ).fetchall()
            for row in rows:
                if str(row["fingerprint"]) in active_fingerprints:
                    continue
                connection.execute(
                    """UPDATE repair_queue
                       SET state='queued', verification_json=?, next_attempt_at=?,
                           owner=NULL, lease_until=0
                       WHERE incident_id=? AND state='blocked'""",
                    (encoded, int(now), int(row["incident_id"])),
                )
                requeued_ids.append(int(row["incident_id"]))
            connection.commit()
            if not requeued_ids:
                return []
            placeholders = ",".join("?" for _ in requeued_ids)
            requeued = connection.execute(
                f"""SELECT * FROM repair_queue
                    WHERE incident_id IN ({placeholders})
                    ORDER BY incident_id""",
                requeued_ids,
            ).fetchall()
        return [self._row(row) for row in requeued]

    def enqueue(
        self,
        *,
        fingerprint: str,
        repair_class: str,
        evidence: dict[str, Any],
        detected_at: int,
    ) -> dict[str, Any]:
        if not fingerprint.strip() or not repair_class.strip():
            raise ValueError("fingerprint and repair_class are required")
        encoded = json.dumps(evidence, ensure_ascii=False, sort_keys=True)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """SELECT * FROM repair_queue
                   WHERE fingerprint=? AND state IN ('queued','claimed','blocked')""",
                (fingerprint,),
            ).fetchone()
            if existing is not None:
                connection.execute(
                    """UPDATE repair_queue
                       SET occurrence_count=occurrence_count+1,
                           last_detected_at=?, evidence_json=?
                       WHERE incident_id=?""",
                    (detected_at, encoded, existing["incident_id"]),
                )
                row = connection.execute(
                    "SELECT * FROM repair_queue WHERE incident_id=?",
                    (existing["incident_id"],),
                ).fetchone()
                connection.commit()
                return self._row(row)
            cursor = connection.execute(
                """INSERT INTO repair_queue(
                       fingerprint,repair_class,evidence_json,
                       first_detected_at,last_detected_at
                   ) VALUES(?,?,?,?,?)""",
                (fingerprint, repair_class, encoded, detected_at, detected_at),
            )
            row = connection.execute(
                "SELECT * FROM repair_queue WHERE incident_id=?",
                (cursor.lastrowid,),
            ).fetchone()
            connection.commit()
        return self._row(row)

    def claim(
        self,
        *,
        owner: str,
        now: int,
        lease_seconds: int,
        allowed_classes: set[str] | None = None,
    ) -> dict[str, Any] | None:
        if not owner.strip() or lease_seconds <= 0:
            raise ValueError("owner and positive lease_seconds are required")
        if allowed_classes is not None and not allowed_classes:
            return None
        class_clause = ""
        parameters: list[Any] = [now, now]
        if allowed_classes is not None:
            classes = sorted(allowed_classes)
            class_clause = f" AND repair_class IN ({','.join('?' for _ in classes)})"
            parameters.extend(classes)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                f"""SELECT * FROM repair_queue
                   WHERE ((state='queued' AND next_attempt_at <= ?)
                      OR (state='claimed' AND lease_until < ?))
                   {class_clause}
                   ORDER BY incident_id
                   LIMIT 1""",
                parameters,
            ).fetchone()
            if row is None:
                connection.commit()
                return None
            token = int(row["fencing_token"]) + 1
            connection.execute(
                """UPDATE repair_queue
                   SET state='claimed', owner=?, fencing_token=?, lease_until=?
                   WHERE incident_id=?""",
                (owner, token, now + lease_seconds, row["incident_id"]),
            )
            claimed = connection.execute(
                "SELECT * FROM repair_queue WHERE incident_id=?",
                (row["incident_id"],),
            ).fetchone()
            connection.commit()
        return self._row(claimed)

    def recover(
        self,
        incident_id: int,
        *,
        owner: str,
        fencing_token: int,
        verification: dict[str, Any],
        recovered_at: int,
        action: dict[str, Any] | None = None,
        increment_attempt: bool = False,
    ) -> dict[str, Any]:
        encoded = json.dumps(verification, ensure_ascii=False, sort_keys=True)
        encoded_action = (
            json.dumps(action, ensure_ascii=False, sort_keys=True)
            if action is not None
            else None
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """UPDATE repair_queue
                   SET state='recovered', verification_json=?, recovered_at=?,
                       lease_until=0, next_attempt_at=0,
                       last_action_json=COALESCE(?,last_action_json),
                       attempt_count=attempt_count+?
                   WHERE incident_id=? AND state='claimed'
                     AND owner=? AND fencing_token=?""",
                (
                    encoded,
                    recovered_at,
                    encoded_action,
                    int(increment_attempt),
                    incident_id,
                    owner,
                    fencing_token,
                ),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                raise LostLease(f"lost repair lease for incident {incident_id}")
            row = connection.execute(
                "SELECT * FROM repair_queue WHERE incident_id=?",
                (incident_id,),
            ).fetchone()
            connection.commit()
        return self._row(row)

    def defer(
        self,
        incident_id: int,
        *,
        owner: str,
        fencing_token: int,
        verification: dict[str, Any],
        action: dict[str, Any],
        next_attempt_at: int,
    ) -> dict[str, Any]:
        encoded_verification = json.dumps(
            verification, ensure_ascii=False, sort_keys=True
        )
        encoded_action = json.dumps(action, ensure_ascii=False, sort_keys=True)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """UPDATE repair_queue
                   SET state='queued', verification_json=?,
                       last_action_json=?, attempt_count=attempt_count+1,
                       next_attempt_at=?, owner=NULL, lease_until=0
                   WHERE incident_id=? AND state='claimed'
                     AND owner=? AND fencing_token=?""",
                (
                    encoded_verification,
                    encoded_action,
                    next_attempt_at,
                    incident_id,
                    owner,
                    fencing_token,
                ),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                raise LostLease(f"lost repair lease for incident {incident_id}")
            row = connection.execute(
                "SELECT * FROM repair_queue WHERE incident_id=?",
                (incident_id,),
            ).fetchone()
            connection.commit()
        return self._row(row)

    def block(
        self,
        incident_id: int,
        *,
        owner: str,
        fencing_token: int,
        verification: dict[str, Any],
        blocked_at: int,
        action: dict[str, Any] | None = None,
        increment_attempt: bool = False,
    ) -> dict[str, Any]:
        encoded_verification = json.dumps(
            verification, ensure_ascii=False, sort_keys=True
        )
        encoded_action = (
            json.dumps(action, ensure_ascii=False, sort_keys=True)
            if action is not None
            else None
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """UPDATE repair_queue
                   SET state='blocked', verification_json=?, blocked_at=?,
                       last_action_json=COALESCE(?,last_action_json),
                       attempt_count=attempt_count+?,
                       owner=NULL, lease_until=0
                   WHERE incident_id=? AND state='claimed'
                     AND owner=? AND fencing_token=?""",
                (
                    encoded_verification,
                    blocked_at,
                    encoded_action,
                    int(increment_attempt),
                    incident_id,
                    owner,
                    fencing_token,
                ),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                raise LostLease(f"lost repair lease for incident {incident_id}")
            row = connection.execute(
                "SELECT * FROM repair_queue WHERE incident_id=?",
                (incident_id,),
            ).fetchone()
            connection.commit()
        return self._row(row)
