from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SessionHandleV1:
    schema_version: int
    endpoint: str
    row_run_id: str
    page_marker: str
    generation: int

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("unsupported SessionHandleV1 schema_version")
        if not self.row_run_id:
            raise ValueError("row_run_id is required")
