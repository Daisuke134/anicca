from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


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


@dataclass(frozen=True, slots=True)
class ActionTargetV1:
    role: str
    label: str
    exact: bool = True


@dataclass(frozen=True, slots=True)
class VisibleActionV1:
    kind: Literal["navigate", "click", "type", "select", "upload", "scroll", "wait"]
    target: ActionTargetV1 | None = None
    text: str | None = None
    url: str | None = None
    file_path: Path | None = None
    delta_y: int | None = None
    wait_ms: int | None = None


@dataclass(frozen=True, slots=True)
class ActionReceiptV1:
    schema_version: int
    kind: str
    target_role: str | None
    target_label: str | None
    before_url: str
    after_url: str
    receipt_sha256: str


@dataclass(frozen=True, slots=True)
class PolicyContextV1:
    row_goal: str
    fact_refs: tuple[str, ...]
    observation_sha256: str
    action_receipt_hashes: tuple[str, ...]
    remaining_steps: int


@dataclass(frozen=True, slots=True)
class ActionPlanV1:
    based_on_observation_sha256: str
    action: VisibleActionV1 | None = None
    transition: Literal["checkpointed", "ineligible", "post_submit_verification"] | None = None
    reason: str = ""
