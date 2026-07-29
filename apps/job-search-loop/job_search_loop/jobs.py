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
        }
        return cls(**{key: value for key, value in payload.items() if key in allowed})
