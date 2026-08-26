from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .mercor_work_harness import WorkHarnessError, advance_state


class WorkStoreError(ValueError):
    pass


class WorkStateStore:
    """Private append-only work transition store with idempotent event IDs."""

    def __init__(self, path: Path):
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.path.parent, 0o700)
        if self.path.exists():
            os.chmod(self.path, 0o600)

    def _rows(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                raise WorkStoreError("work event store contains invalid JSON") from error
            if not isinstance(value, dict):
                raise WorkStoreError("work event store row must be an object")
            rows.append(value)
        return rows

    def events(self, work_id: str) -> list[dict[str, Any]]:
        return [row for row in self._rows() if row.get("work_id") == work_id]

    def artifacts(self, work_id: str) -> list[dict[str, Any]]:
        return [row for row in self.events(work_id) if row.get("kind") == "artifact"]

    def current_state(self, work_id: str) -> str:
        rows = self.events(work_id)
        return str(rows[-1]["state"]) if rows else "submitted_pending_review"

    def transition(self, *, work_id: str, event_id: str, next_state: str, evidence_ref: str, **payment: Any) -> dict[str, Any]:
        if not work_id.strip() or not event_id.strip():
            raise WorkStoreError("work_id and event_id are required")
        rows = self._rows()
        existing = next((row for row in rows if row.get("event_id") == event_id), None)
        if existing is not None:
            expected = {"work_id": work_id, "state": next_state, "evidence_ref": evidence_ref}
            if any(existing.get(key) != value for key, value in expected.items()):
                raise WorkStoreError("event_id already exists with different transition")
            return existing
        current = self.current_state(work_id)
        try:
            _, event = advance_state(
                current,
                next_state,
                evidence_ref=evidence_ref,
                **payment,
            )
        except WorkHarnessError as error:
            raise WorkStoreError(str(error)) from error
        event.update({"work_id": work_id, "event_id": event_id})
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(self.path, 0o600)
        return event

    def record_artifact(
        self,
        *,
        work_id: str,
        event_id: str,
        artifact_type: str,
        evidence_ref: str,
        artifact_key: str,
    ) -> dict[str, Any]:
        if not all(isinstance(value, str) and value.strip() for value in (work_id, event_id, artifact_type, evidence_ref, artifact_key)):
            raise WorkStoreError("artifact identity and evidence fields are required")
        rows = self._rows()
        existing = next((row for row in rows if row.get("event_id") == event_id), None)
        expected = {
            "work_id": work_id,
            "event_id": event_id,
            "kind": "artifact",
            "artifact_type": artifact_type,
            "artifact_key": artifact_key,
            "evidence_ref": evidence_ref,
        }
        if existing is not None:
            if any(existing.get(key) != value for key, value in expected.items()):
                raise WorkStoreError("artifact event_id already exists with different data")
            return existing
        event = {
            **expected,
            "state": self.current_state(work_id),
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(self.path, 0o600)
        return event
