from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class ActiveThreadConflict(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ThreadRegistry:
    """Minimal business-work to Codex app-server thread binding."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.connection = sqlite3.connect(path, isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS thread_bindings (
              work_type TEXT NOT NULL,
              work_id TEXT NOT NULL,
              generation INTEGER NOT NULL,
              thread_id TEXT NOT NULL,
              status TEXT NOT NULL CHECK(status IN ('active', 'archived')),
              predecessor_thread_id TEXT,
              created_at TEXT NOT NULL,
              last_resumed_at TEXT NOT NULL,
              archived_at TEXT,
              runtime_release_sha TEXT NOT NULL,
              last_run_id TEXT NOT NULL,
              last_workflow_id TEXT,
              PRIMARY KEY(work_type, work_id, generation),
              UNIQUE(thread_id)
            )
            """
        )
        self.connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS one_active_thread_per_work
            ON thread_bindings(work_type, work_id) WHERE status = 'active'
            """
        )
        os.chmod(path, 0o600)

    def close(self) -> None:
        self.connection.close()

    def bind(
        self,
        *,
        work_type: str,
        work_id: str,
        thread_id: str,
        runtime_release_sha: str,
        run_id: str,
        workflow_id: str | None = None,
    ) -> dict[str, object]:
        values = (work_type, work_id, thread_id, runtime_release_sha, run_id)
        if any(not value or not value.strip() for value in values):
            raise ValueError("thread binding identifiers must be non-empty")
        now = _now()
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            current = self.connection.execute(
                "SELECT * FROM thread_bindings "
                "WHERE work_type=? AND work_id=? AND status='active'",
                (work_type, work_id),
            ).fetchone()
            if current is not None:
                if current["thread_id"] != thread_id:
                    raise ActiveThreadConflict(
                        f"{work_type}/{work_id} is already bound to an active thread"
                    )
                self.connection.execute(
                    "UPDATE thread_bindings SET last_resumed_at=?, "
                    "runtime_release_sha=?, last_run_id=?, last_workflow_id=? "
                    "WHERE work_type=? AND work_id=? AND generation=?",
                    (
                        now,
                        runtime_release_sha,
                        run_id,
                        workflow_id,
                        work_type,
                        work_id,
                        current["generation"],
                    ),
                )
            else:
                previous = self.connection.execute(
                    "SELECT generation, thread_id FROM thread_bindings "
                    "WHERE work_type=? AND work_id=? ORDER BY generation DESC LIMIT 1",
                    (work_type, work_id),
                ).fetchone()
                generation = 1 if previous is None else int(previous["generation"]) + 1
                predecessor = None if previous is None else previous["thread_id"]
                self.connection.execute(
                    "INSERT INTO thread_bindings VALUES(?,?,?,?,?,?,?,?,NULL,?,?,?)",
                    (
                        work_type,
                        work_id,
                        generation,
                        thread_id,
                        "active",
                        predecessor,
                        now,
                        now,
                        runtime_release_sha,
                        run_id,
                        workflow_id,
                    ),
                )
            self.connection.execute("COMMIT")
        except Exception:
            self.connection.execute("ROLLBACK")
            raise
        return self.active(work_type, work_id)

    def archive(self, work_type: str, work_id: str) -> None:
        now = _now()
        changed = self.connection.execute(
            "UPDATE thread_bindings SET status='archived', archived_at=? "
            "WHERE work_type=? AND work_id=? AND status='active'",
            (now, work_type, work_id),
        ).rowcount
        if changed != 1:
            raise KeyError((work_type, work_id))

    def active(self, work_type: str, work_id: str) -> dict[str, object]:
        row = self.connection.execute(
            "SELECT * FROM thread_bindings "
            "WHERE work_type=? AND work_id=? AND status='active'",
            (work_type, work_id),
        ).fetchone()
        if row is None:
            raise KeyError((work_type, work_id))
        return dict(row)
