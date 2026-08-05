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
    clearance_requirement: str = "none"
    skills: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    language_gate: str = "PASS"
    language_note: str | None = None
    deadline: str | None = None
    strengths: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    travel_scope: str = "unspecified"
    frequent_client_site: bool = False

    def __post_init__(self) -> None:
        allowed_clearance = {
            "none",
            "unspecified_required",
            "current_required",
            "obtainable_after_hire",
        }
        if self.clearance_requirement not in allowed_clearance:
            raise ValueError("clearance_requirement is invalid")
        if self.clearance_required and self.clearance_requirement == "none":
            object.__setattr__(self, "clearance_requirement", "unspecified_required")
        elif not self.clearance_required and self.clearance_requirement != "none":
            raise ValueError("clearance requirement conflicts with clearance_required")
        if self.language_gate not in {"PASS", "FAIL", "FLAG"}:
            raise ValueError("language_gate must be PASS, FAIL, or FLAG")
        if self.language_gate != "PASS" and not str(self.language_note or "").strip():
            raise ValueError("language_note is required for FAIL or FLAG")
        if self.travel_scope not in {
            "unspecified",
            "none",
            "domestic",
            "international",
            "domestic_and_international",
        }:
            raise ValueError("travel_scope is invalid")
        if not isinstance(self.frequent_client_site, bool):
            raise ValueError("frequent_client_site must be boolean")

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
            "clearance_requirement",
            "skills",
            "domains",
            "language_gate",
            "language_note",
            "deadline",
            "strengths",
            "gaps",
            "travel_scope",
            "frequent_client_site",
        }
        return cls(**{key: value for key, value in payload.items() if key in allowed})
