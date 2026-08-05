from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Job:
    company: str
    title: str
    url: str
    location: str
    japan_eligible: bool
    compensation_min_jpy: int | None
    clearance_required: bool
    skills: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    language_gate: str = "PASS"
    language_note: str | None = None
    deadline: str | None = None
    strengths: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.language_gate not in {"PASS", "FAIL", "FLAG"}:
            raise ValueError("language_gate must be PASS, FAIL, or FLAG")
        if self.language_gate != "PASS" and not str(self.language_note or "").strip():
            raise ValueError("language_note is required for FAIL or FLAG")

    @classmethod
    def from_extracted(cls, payload: dict[str, Any]) -> "Job":
        extracted = payload.get("extracted", {})
        if not isinstance(extracted, dict):
            raise ValueError("extracted must be an object")
        for name, item in extracted.items():
            if not isinstance(item, dict) or not str(item.get("source_span", "")).strip():
                raise ValueError(f"{name}.source_span is required")
        allowed = {
            "company",
            "title",
            "url",
            "location",
            "japan_eligible",
            "compensation_min_jpy",
            "clearance_required",
            "skills",
            "domains",
            "language_gate",
            "language_note",
            "deadline",
            "strengths",
            "gaps",
        }
        return cls(**{key: value for key, value in payload.items() if key in allowed})
