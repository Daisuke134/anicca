from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class HumanGateError(ValueError):
    pass


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
        gate_id = hashlib.sha256(f"{reason}\n{evidence_ref}".encode()).hexdigest()[:24]
        rows = self._rows()
        existing = next((row for row in rows if row.get("gate_id") == gate_id), None)
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
        return [row for row in self._rows() if row.get("status") == "pending"]
