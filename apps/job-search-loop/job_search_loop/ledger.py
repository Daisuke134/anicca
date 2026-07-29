from __future__ import annotations

import hashlib
import json
import os
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
                "SELECT intent_id FROM submit_intents WHERE application_id = ?",
                (application_id,),
            ).fetchone()
            if existing:
                return None
            if self.current_state(application_id) != "materials_ready":
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
            intent = SubmitIntent(
                intent_id=uuid.uuid4().hex,
                application_id=application_id,
                fence=1,
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
                    _now(),
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
            self.connection.execute(
                """
                UPDATE submit_intents SET status = ?, completed_at = ?
                WHERE intent_id = ? AND fence = ?
                """,
                (outcome, _now(), intent_id, fence),
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
