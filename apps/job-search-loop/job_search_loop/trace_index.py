from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from .telemetry import ALLOWED_ATTRIBUTES


def _attribute_value(value: dict[str, Any]) -> Any:
    for key in ("stringValue", "intValue", "doubleValue", "boolValue"):
        if key in value:
            return value[key]
    return None


class TraceIndex:
    def __init__(self, path: Path):
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.connection = sqlite3.connect(self.path)
        os.chmod(self.path, 0o600)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS spans("
            "trace_id TEXT NOT NULL,span_id TEXT NOT NULL,name TEXT NOT NULL,"
            "start_time_unix_nano INTEGER NOT NULL,end_time_unix_nano INTEGER NOT NULL,"
            "application_id TEXT,failure_code TEXT,attributes_json TEXT NOT NULL,"
            "PRIMARY KEY(trace_id,span_id))"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS spans_failure_start "
            "ON spans(failure_code,start_time_unix_nano)"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS spans_application_start "
            "ON spans(application_id,start_time_unix_nano)"
        )
        self.connection.commit()

    def ingest(self, source: Path) -> int:
        inserted = 0
        for line in Path(source).read_text(encoding="utf-8").splitlines():
            value = json.loads(line)
            for resource in value.get("resourceSpans", []):
                for scope in resource.get("scopeSpans", []):
                    for span in scope.get("spans", []):
                        attributes = {
                            row["key"]: _attribute_value(row.get("value", {}))
                            for row in span.get("attributes", [])
                            if row.get("key") in ALLOWED_ATTRIBUTES
                        }
                        changed = self.connection.execute(
                            "INSERT OR IGNORE INTO spans VALUES(?,?,?,?,?,?,?,?)",
                            (
                                span.get("traceId"), span.get("spanId"), span.get("name"),
                                int(span.get("startTimeUnixNano") or 0),
                                int(span.get("endTimeUnixNano") or 0),
                                attributes.get("application.id"),
                                attributes.get("failure.code"),
                                json.dumps(attributes, sort_keys=True, separators=(",", ":")),
                            ),
                        ).rowcount
                        inserted += int(changed)
        self.connection.commit()
        return inserted

    def query(self, *, failure_code: str | None = None,
              application_id: str | None = None) -> list[dict[str, Any]]:
        clauses, values = [], []
        if failure_code is not None:
            clauses.append("failure_code=?")
            values.append(failure_code)
        if application_id is not None:
            clauses.append("application_id=?")
            values.append(application_id)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = self.connection.execute(
            "SELECT * FROM spans" + where + " ORDER BY start_time_unix_nano DESC",
            values,
        ).fetchall()
        return [dict(row) for row in rows]

    def prune_before(self, cutoff_unix_nano: int) -> int:
        changed = self.connection.execute(
            "DELETE FROM spans WHERE start_time_unix_nano < ?", (cutoff_unix_nano,)
        ).rowcount
        self.connection.commit()
        return int(changed)

    def close(self) -> None:
        self.connection.close()
