from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class HumanGateError(ValueError):
    pass


def _identity(reason: str, evidence_ref: str) -> str:
    """Return a stable logical identity despite model wording drift."""
    normalized = " ".join(reason.casefold().split())
    if "project thor assessment" in normalized:
        return "project_thor_assessment"
    if "finance interview" in normalized:
        return "finance_interview"
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized).strip()
    return f"{normalized}\n{evidence_ref.strip()}"


class HumanGateStore:
    def __init__(self, path: Path):
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.path.parent, 0o700)
        if self.path.exists():
            os.chmod(self.path, 0o600)

    def _rows(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        rows = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise HumanGateError("human gate row must be an object")
            rows.append(value)
        return rows

    def record(self, *, run_id: str, reason: str, evidence_ref: str) -> dict[str, Any]:
        if not all(isinstance(value, str) and value.strip() for value in (run_id, reason, evidence_ref)):
            raise HumanGateError("run_id, reason, and evidence_ref are required")
        identity = _identity(reason.strip(), evidence_ref.strip())
        gate_id = hashlib.sha256(identity.encode()).hexdigest()[:24]
        rows = self._rows()
        existing = next(
            (
                row
                for row in rows
                if _identity(str(row.get("reason", "")), str(row.get("evidence_ref", ""))) == identity
            ),
            None,
        )
        if existing is not None:
            return existing
        row = {
            "gate_id": gate_id,
            "run_id": run_id.strip(),
            "reason": reason.strip(),
            "evidence_ref": evidence_ref.strip(),
            "status": "pending",
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(self.path, 0o600)
        return row

    def pending(self) -> list[dict[str, Any]]:
        pending: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in self._rows():
            if row.get("status") != "pending":
                continue
            identity = _identity(str(row.get("reason", "")), str(row.get("evidence_ref", "")))
            if identity in seen:
                continue
            seen.add(identity)
            pending.append(row)
        return pending
