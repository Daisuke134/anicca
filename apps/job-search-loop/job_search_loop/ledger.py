from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .ats import evaluate_snapshot
from .state import canonical_job_id, canonical_url, validate_transition


class FenceError(RuntimeError):
    pass


@dataclass(frozen=True)
class SubmitIntent:
    intent_id: str
    application_id: str
    fence: int
    payload_hash: str
    resume_path: str
    resume_sha256: str
    ats_snapshot_path: str
    ats_snapshot_sha256: str
    japan_day: str
    slot: int


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Ledger:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.path.parent, 0o700)
        self.connection = sqlite3.connect(
            self.path, timeout=10, isolation_level=None
        )
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id TEXT PRIMARY KEY,
                company TEXT NOT NULL,
                title TEXT NOT NULL,
                canonical_url TEXT NOT NULL,
                current_state TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                application_id TEXT NOT NULL REFERENCES applications(id),
                from_state TEXT,
                to_state TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS submit_intents (
                intent_id TEXT PRIMARY KEY,
                application_id TEXT NOT NULL UNIQUE REFERENCES applications(id),
                fence INTEGER NOT NULL,
                payload_hash TEXT NOT NULL,
                resume_path TEXT,
                resume_sha256 TEXT,
                ats_snapshot_path TEXT,
                ats_snapshot_sha256 TEXT,
                japan_day TEXT NOT NULL,
                slot INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS daily_slots (
                japan_day TEXT NOT NULL,
                slot INTEGER NOT NULL,
                application_id TEXT NOT NULL UNIQUE REFERENCES applications(id),
                status TEXT NOT NULL,
                PRIMARY KEY (japan_day, slot)
            );
            CREATE TABLE IF NOT EXISTS submission_attempts (
                intent_id TEXT NOT NULL REFERENCES submit_intents(intent_id),
                fence INTEGER NOT NULL,
                application_id TEXT NOT NULL REFERENCES applications(id),
                payload_hash TEXT NOT NULL,
                resume_path TEXT,
                resume_sha256 TEXT,
                ats_snapshot_path TEXT,
                ats_snapshot_sha256 TEXT,
                japan_day TEXT NOT NULL,
                slot INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                PRIMARY KEY (intent_id, fence)
            );
            CREATE TABLE IF NOT EXISTS submission_confirmations (
                message_id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                intent_id TEXT NOT NULL UNIQUE
                    REFERENCES submit_intents(intent_id),
                evidence_sha256 TEXT NOT NULL,
                received_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        intent_columns = {
            str(row["name"])
            for row in self.connection.execute("PRAGMA table_info(submit_intents)")
        }
        if "resume_path" not in intent_columns:
            self.connection.execute(
                "ALTER TABLE submit_intents ADD COLUMN resume_path TEXT"
            )
        if "resume_sha256" not in intent_columns:
            self.connection.execute(
                "ALTER TABLE submit_intents ADD COLUMN resume_sha256 TEXT"
            )
        if "ats_snapshot_path" not in intent_columns:
            self.connection.execute(
                "ALTER TABLE submit_intents ADD COLUMN ats_snapshot_path TEXT"
            )
        if "ats_snapshot_sha256" not in intent_columns:
            self.connection.execute(
                "ALTER TABLE submit_intents ADD COLUMN ats_snapshot_sha256 TEXT"
            )
        self.connection.execute(
            """
            INSERT OR IGNORE INTO submission_attempts
              (intent_id, fence, application_id, payload_hash, resume_path,
               resume_sha256, ats_snapshot_path, ats_snapshot_sha256,
               japan_day, slot, status, created_at, completed_at)
            SELECT
              intent_id, fence, application_id, payload_hash, resume_path,
              resume_sha256, ats_snapshot_path, ats_snapshot_sha256,
              japan_day, slot, status, created_at, completed_at
            FROM submit_intents
            """
        )
        if self.path.exists():
            os.chmod(self.path, 0o600)

    def close(self) -> None:
        self.connection.close()

    @contextmanager
    def _transaction(self) -> Iterator[None]:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()

    def _append_event(
        self,
        application_id: str,
        from_state: str | None,
        to_state: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO events
              (event_id, application_id, from_state, to_state, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                uuid.uuid4().hex,
                application_id,
                from_state,
                to_state,
                json.dumps(payload or {}, ensure_ascii=False, sort_keys=True),
                _now(),
            ),
        )

    def add_application(self, company: str, title: str, url: str) -> str:
        application_id = canonical_job_id(company, title, url)
        with self._transaction():
            existing = self.connection.execute(
                "SELECT id FROM applications WHERE id = ?", (application_id,)
            ).fetchone()
            if existing:
                return str(existing["id"])
            self.connection.execute(
                """
                INSERT INTO applications
                  (id, company, title, canonical_url, current_state, created_at)
                VALUES (?, ?, ?, ?, 'discovered', ?)
                """,
                (
                    application_id,
                    company.strip(),
                    title.strip(),
                    canonical_url(url),
                    _now(),
                ),
            )
            self._append_event(application_id, None, "discovered")
        return application_id

    def current_state(self, application_id: str) -> str:
        row = self.connection.execute(
            "SELECT current_state FROM applications WHERE id = ?",
            (application_id,),
        ).fetchone()
        if row is None:
            raise KeyError(application_id)
        return str(row["current_state"])

    def daily_slot_count(self, japan_day: str) -> int:
        row = self.connection.execute(
            "SELECT COUNT(*) AS count FROM daily_slots WHERE japan_day = ?",
            (japan_day,),
        ).fetchone()
        return int(row["count"])

    def _transition_in_transaction(
        self,
        application_id: str,
        to_state: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        from_state = self.current_state(application_id)
        validate_transition(from_state, to_state)
        self.connection.execute(
            "UPDATE applications SET current_state = ? WHERE id = ?",
            (to_state, application_id),
        )
        self._append_event(application_id, from_state, to_state, payload)

    def transition(
        self,
        application_id: str,
        to_state: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        with self._transaction():
            self._transition_in_transaction(application_id, to_state, payload)

    def events(self, application_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT event_id, from_state, to_state, payload_json, created_at
            FROM events WHERE application_id = ? ORDER BY rowid
            """,
            (application_id,),
        ).fetchall()
        return [
            {
                "event_id": row["event_id"],
                "from_state": row["from_state"],
                "to_state": row["to_state"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def application_summary_rows(self) -> list[dict[str, str | None]]:
        rows = self.connection.execute(
            """
            SELECT
              applications.canonical_url,
              applications.current_state,
              submit_intents.status AS submission_state
            FROM applications
            LEFT JOIN submit_intents
              ON submit_intents.application_id = applications.id
            ORDER BY applications.created_at, applications.rowid
            """
        ).fetchall()
        return [
            {
                "canonical_url": str(row["canonical_url"]),
                "current_state": str(row["current_state"]),
                "submission_state": (
                    str(row["submission_state"])
                    if row["submission_state"] is not None
                    else None
                ),
            }
            for row in rows
        ]

    def retryable_applications(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT
              applications.id AS application_id,
              applications.company,
              applications.title,
              applications.canonical_url,
              submit_intents.intent_id,
              submit_intents.fence
            FROM submit_intents
            JOIN applications ON applications.id = submit_intents.application_id
            WHERE submit_intents.status = 'not_submitted'
              AND applications.current_state = 'not_submitted'
            ORDER BY submit_intents.completed_at, submit_intents.rowid
            """
        ).fetchall()
        return [
            {
                "application_id": str(row["application_id"]),
                "company": str(row["company"]),
                "title": str(row["title"]),
                "canonical_url": str(row["canonical_url"]),
                "intent_id": str(row["intent_id"]),
                "fence": int(row["fence"]),
            }
            for row in rows
        ]

    def submission_attempts(self, application_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT
              intent_id, fence, payload_hash, resume_path, resume_sha256,
              ats_snapshot_path, ats_snapshot_sha256, japan_day, slot,
              status, created_at, completed_at
            FROM submission_attempts
            WHERE application_id = ?
            ORDER BY fence
            """,
            (application_id,),
        ).fetchall()
        return [
            {
                "intent_id": str(row["intent_id"]),
                "fence": int(row["fence"]),
                "payload_hash": str(row["payload_hash"]),
                "resume_path": row["resume_path"],
                "resume_sha256": row["resume_sha256"],
                "ats_snapshot_path": row["ats_snapshot_path"],
                "ats_snapshot_sha256": row["ats_snapshot_sha256"],
                "japan_day": str(row["japan_day"]),
                "slot": int(row["slot"]),
                "status": str(row["status"]),
                "created_at": str(row["created_at"]),
                "completed_at": row["completed_at"],
            }
            for row in rows
        ]

    def claim_submission(
        self,
        application_id: str,
        japan_day: str,
        payload_hash: str,
        *,
        resume_path: Path,
        resume_sha256: str,
        ats_snapshot_path: Path,
        ats_snapshot_sha256: str,
    ) -> SubmitIntent | None:
        resolved_resume = Path(resume_path).expanduser().resolve()
        if not resolved_resume.is_file():
            raise ValueError(f"resume is not a file: {resolved_resume}")
        actual_resume_sha256 = hashlib.sha256(resolved_resume.read_bytes()).hexdigest()
        if actual_resume_sha256 != resume_sha256:
            raise ValueError("resume SHA-256 does not match the selected file")
        resolved_snapshot = Path(ats_snapshot_path).expanduser().resolve()
        if not resolved_snapshot.is_file():
            raise ValueError(
                f"ATS snapshot SHA-256 cannot be verified: not a file: {resolved_snapshot}"
            )
        snapshot_bytes = resolved_snapshot.read_bytes()
        actual_snapshot_sha256 = hashlib.sha256(snapshot_bytes).hexdigest()
        if actual_snapshot_sha256 != ats_snapshot_sha256:
            raise ValueError("ATS snapshot SHA-256 does not match the selected file")
        try:
            snapshot = json.loads(snapshot_bytes)
            snapshot_evaluation = evaluate_snapshot(snapshot)
        except (json.JSONDecodeError, ValueError) as error:
            raise ValueError(f"ATS snapshot is invalid: {error}") from error
        if not snapshot_evaluation["ready"]:
            blockers = ",".join(snapshot_evaluation["blockers"])
            raise ValueError(f"ATS snapshot is not ready: {blockers}")
        if not snapshot_evaluation["claim_ready"]:
            raise ValueError("ATS snapshot is not claim-ready: application form not open")
        with self._transaction():
            application = self.connection.execute(
                "SELECT canonical_url FROM applications WHERE id = ?",
                (application_id,),
            ).fetchone()
            if application is None:
                raise KeyError(application_id)
            if canonical_url(snapshot["url"]) != str(application["canonical_url"]):
                raise ValueError("ATS snapshot URL does not match the application")
            existing = self.connection.execute(
                "SELECT * FROM submit_intents WHERE application_id = ?",
                (application_id,),
            ).fetchone()
            current_state = self.current_state(application_id)
            reopening = (
                existing is not None
                and str(existing["status"]) == "not_submitted"
                and current_state == "not_submitted"
            )
            if existing is not None and not reopening:
                return None
            if existing is None and current_state != "materials_ready":
                return None
            used = {
                int(row["slot"])
                for row in self.connection.execute(
                    "SELECT slot FROM daily_slots WHERE japan_day = ?",
                    (japan_day,),
                ).fetchall()
            }
            slot = next((candidate for candidate in (1, 2) if candidate not in used), None)
            if slot is None:
                return None
            claimed_at = _now()
            intent = SubmitIntent(
                intent_id=(
                    str(existing["intent_id"]) if reopening else uuid.uuid4().hex
                ),
                application_id=application_id,
                fence=(int(existing["fence"]) + 1 if reopening else 1),
                payload_hash=payload_hash,
                resume_path=str(resolved_resume),
                resume_sha256=resume_sha256,
                ats_snapshot_path=str(resolved_snapshot),
                ats_snapshot_sha256=ats_snapshot_sha256,
                japan_day=japan_day,
                slot=slot,
            )
            self.connection.execute(
                """
                INSERT INTO daily_slots (japan_day, slot, application_id, status)
                VALUES (?, ?, ?, 'claimed')
                """,
                (japan_day, slot, application_id),
            )
            if reopening:
                self.connection.execute(
                    """
                    UPDATE submit_intents
                    SET fence = ?, payload_hash = ?, resume_path = ?,
                        resume_sha256 = ?, ats_snapshot_path = ?,
                        ats_snapshot_sha256 = ?, japan_day = ?, slot = ?,
                        status = 'submit_claimed', created_at = ?,
                        completed_at = NULL
                    WHERE intent_id = ? AND fence = ? AND status = 'not_submitted'
                    """,
                    (
                        intent.fence,
                        intent.payload_hash,
                        intent.resume_path,
                        intent.resume_sha256,
                        intent.ats_snapshot_path,
                        intent.ats_snapshot_sha256,
                        intent.japan_day,
                        intent.slot,
                        claimed_at,
                        intent.intent_id,
                        int(existing["fence"]),
                    ),
                )
            else:
                self.connection.execute(
                    """
                    INSERT INTO submit_intents
                      (intent_id, application_id, fence, payload_hash, resume_path,
                       resume_sha256, ats_snapshot_path, ats_snapshot_sha256,
                       japan_day, slot, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'submit_claimed', ?)
                    """,
                    (
                        intent.intent_id,
                        intent.application_id,
                        intent.fence,
                        intent.payload_hash,
                        intent.resume_path,
                        intent.resume_sha256,
                        intent.ats_snapshot_path,
                        intent.ats_snapshot_sha256,
                        intent.japan_day,
                        intent.slot,
                        claimed_at,
                    ),
                )
            self.connection.execute(
                """
                INSERT INTO submission_attempts
                  (intent_id, fence, application_id, payload_hash, resume_path,
                   resume_sha256, ats_snapshot_path, ats_snapshot_sha256,
                   japan_day, slot, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'submit_claimed', ?)
                """,
                (
                    intent.intent_id,
                    intent.fence,
                    intent.application_id,
                    intent.payload_hash,
                    intent.resume_path,
                    intent.resume_sha256,
                    intent.ats_snapshot_path,
                    intent.ats_snapshot_sha256,
                    intent.japan_day,
                    intent.slot,
                    claimed_at,
                ),
            )
            self._transition_in_transaction(
                application_id,
                "submit_claimed",
                {
                    "intent_id": intent.intent_id,
                    "fence": intent.fence,
                    "payload_hash": payload_hash,
                    "resume_sha256": resume_sha256,
                    "ats_snapshot_sha256": ats_snapshot_sha256,
                },
            )
            return intent

    def complete_submission(
        self, intent_id: str, fence: int, outcome: str
    ) -> None:
        if outcome not in {"submitted", "submit_unknown", "not_submitted"}:
            raise ValueError(f"invalid submission outcome: {outcome}")
        with self._transaction():
            row = self.connection.execute(
                "SELECT * FROM submit_intents WHERE intent_id = ?", (intent_id,)
            ).fetchone()
            if row is None or int(row["fence"]) != fence:
                raise FenceError("submission fence does not match")
            if row["status"] != "submit_claimed":
                raise FenceError("submission intent is already completed")
            completed_at = _now()
            self.connection.execute(
                """
                UPDATE submit_intents SET status = ?, completed_at = ?
                WHERE intent_id = ? AND fence = ?
                """,
                (outcome, completed_at, intent_id, fence),
            )
            self.connection.execute(
                """
                UPDATE submission_attempts SET status = ?, completed_at = ?
                WHERE intent_id = ? AND fence = ?
                """,
                (outcome, completed_at, intent_id, fence),
            )
            self.connection.execute(
                """
                UPDATE daily_slots SET status = ?
                WHERE japan_day = ? AND slot = ? AND application_id = ?
                """,
                (outcome, row["japan_day"], row["slot"], row["application_id"]),
            )
            self._transition_in_transaction(
                str(row["application_id"]),
                outcome,
                {"intent_id": intent_id, "fence": fence},
            )
            if outcome == "not_submitted":
                self.connection.execute(
                    """
                    DELETE FROM daily_slots
                    WHERE japan_day = ? AND slot = ? AND application_id = ?
                    """,
                    (row["japan_day"], row["slot"], row["application_id"]),
                )

    def reconcile_submission_confirmation(
        self,
        *,
        intent_id: str,
        message_id: str,
        thread_id: str,
        evidence_sha256: str,
        received_at: str,
    ) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", message_id):
            raise ValueError("invalid Gmail message ID")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", thread_id):
            raise ValueError("invalid Gmail thread ID")
        if not re.fullmatch(r"[a-f0-9]{64}", evidence_sha256):
            raise ValueError("invalid confirmation evidence hash")
        try:
            received = datetime.fromisoformat(received_at)
        except ValueError as error:
            raise ValueError("received_at must be RFC3339") from error
        if received.tzinfo is None:
            raise ValueError("received_at must include a timezone")

        with self._transaction():
            existing_message = self.connection.execute(
                """
                SELECT thread_id, intent_id, evidence_sha256, received_at
                FROM submission_confirmations
                WHERE message_id = ?
                """,
                (message_id,),
            ).fetchone()
            if existing_message is not None:
                expected = (
                    thread_id,
                    intent_id,
                    evidence_sha256,
                    received_at,
                )
                actual = (
                    str(existing_message["thread_id"]),
                    str(existing_message["intent_id"]),
                    str(existing_message["evidence_sha256"]),
                    str(existing_message["received_at"]),
                )
                if actual != expected:
                    raise FenceError(
                        "Gmail message ID is already bound to different evidence"
                    )
                return "duplicate"

            existing_intent = self.connection.execute(
                """
                SELECT message_id
                FROM submission_confirmations
                WHERE intent_id = ?
                """,
                (intent_id,),
            ).fetchone()
            if existing_intent is not None:
                raise FenceError(
                    "submission intent already has a different confirmation"
                )

            row = self.connection.execute(
                """
                SELECT
                  submit_intents.*,
                  applications.current_state
                FROM submit_intents
                JOIN applications
                  ON applications.id = submit_intents.application_id
                WHERE submit_intents.intent_id = ?
                """,
                (intent_id,),
            ).fetchone()
            if row is None:
                raise FenceError("submission intent does not exist")
            if (
                str(row["status"]) != "submit_unknown"
                or str(row["current_state"]) != "submit_unknown"
            ):
                raise FenceError(
                    "only a submit_unknown application can be reconciled"
                )
            intent_created = datetime.fromisoformat(str(row["created_at"]))
            if received < intent_created:
                raise FenceError("confirmation predates the submission intent")

            created_at = _now()
            self.connection.execute(
                """
                INSERT INTO submission_confirmations
                  (message_id, thread_id, intent_id, evidence_sha256,
                   received_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    thread_id,
                    intent_id,
                    evidence_sha256,
                    received_at,
                    created_at,
                ),
            )
            intent_update = self.connection.execute(
                """
                UPDATE submit_intents
                SET status = 'submitted'
                WHERE intent_id = ? AND status = 'submit_unknown'
                """,
                (intent_id,),
            )
            attempt_update = self.connection.execute(
                """
                UPDATE submission_attempts
                SET status = 'submitted'
                WHERE intent_id = ? AND fence = ? AND status = 'submit_unknown'
                """,
                (intent_id, int(row["fence"])),
            )
            slot_update = self.connection.execute(
                """
                UPDATE daily_slots
                SET status = 'submitted'
                WHERE japan_day = ? AND slot = ? AND application_id = ?
                  AND status = 'submit_unknown'
                """,
                (
                    str(row["japan_day"]),
                    int(row["slot"]),
                    str(row["application_id"]),
                ),
            )
            if (
                intent_update.rowcount != 1
                or attempt_update.rowcount != 1
                or slot_update.rowcount != 1
            ):
                raise FenceError("submission confirmation state is inconsistent")
            application_id = str(row["application_id"])
            application_update = self.connection.execute(
                """
                UPDATE applications
                SET current_state = 'submitted'
                WHERE id = ? AND current_state = 'submit_unknown'
                """,
                (application_id,),
            )
            if application_update.rowcount != 1:
                raise FenceError("application confirmation state is inconsistent")
            self._append_event(
                application_id,
                "submit_unknown",
                "submitted",
                {
                    "intent_id": intent_id,
                    "message_id": message_id,
                    "thread_id": thread_id,
                    "evidence_sha256": evidence_sha256,
                    "received_at": received_at,
                },
            )
            return "reconciled"

    def submitted_resume_reports(self) -> list[dict[str, str]]:
        rows = self.connection.execute(
            """
            SELECT
              applications.id AS application_id,
              applications.company,
              applications.title,
              applications.canonical_url,
              submit_intents.resume_path,
              submit_intents.resume_sha256
            FROM submit_intents
            JOIN applications ON applications.id = submit_intents.application_id
            WHERE submit_intents.status = 'submitted'
              AND submit_intents.resume_path IS NOT NULL
              AND submit_intents.resume_sha256 IS NOT NULL
            ORDER BY submit_intents.completed_at, submit_intents.rowid
            """
        ).fetchall()
        return [
            {
                "application_id": str(row["application_id"]),
                "company": str(row["company"]),
                "title": str(row["title"]),
                "canonical_url": str(row["canonical_url"]),
                "resume_path": str(row["resume_path"]),
                "resume_sha256": str(row["resume_sha256"]),
            }
            for row in rows
        ]
