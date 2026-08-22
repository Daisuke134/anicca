from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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


@dataclass(frozen=True, slots=True)
class VisibleControlV1:
    tag: str
    role: str
    control_type: str
    label: str
    disabled: bool


@dataclass(frozen=True, slots=True)
class ObservationV1:
    schema_version: int
    url: str
    title: str
    visible_text: str
    controls: tuple[VisibleControlV1, ...]
    validation_text: tuple[str, ...]
    tabs: tuple[str, ...]
    screenshot_path: Path
    screenshot_sha256: str
    content_sha256: str
