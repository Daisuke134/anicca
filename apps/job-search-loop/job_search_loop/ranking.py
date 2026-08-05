from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from .jobs import Job


COMPENSATION_FLOOR_JPY = 8_000_000
COMPENSATION_TARGET_JPY = 10_000_000
AUTO_APPLY_THRESHOLD = 75
AI_TERMS = (
    "artificial intelligence",
    "machine learning",
    "agent",
    "genai",
    "generative ai",
    "llm",
    "rag",
)
ENTERPRISE_SKILLS = {
    "agents",
    "databricks",
    "salesforce",
    "agentforce",
    "crm",
    "financial_services",
}
CONSUMER_SKILLS = {"consumer", "swift", "ios", "growth", "product"}
PREFERRED_DOMAINS = {"enterprise_ai", "fintech", "crypto", "consumer_ai"}


@dataclass(frozen=True)
class Evaluation:
    eligible: bool
    score: int
    components: dict[str, int]
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    language_gate: str
    language_note: str | None
    deadline: str | None
    strengths: tuple[str, ...]
    gaps: tuple[str, ...]


def _has_ai_evidence(title: str, skills: set[str]) -> bool:
    title_text = title.casefold()
    if re.search(r"\bai\b", title_text):
        return True
    if any(term in title_text for term in AI_TERMS):
        return True
    return any(
        skill == "ai" or any(term in skill for term in AI_TERMS)
        for skill in skills
    )


def evaluate(job: Job, *, today: date | None = None) -> Evaluation:
    reasons: list[str] = []
    warnings: list[str] = []
    if not job.japan_eligible:
        reasons.append("not_available_from_japan")
    if job.clearance_required:
        reasons.append("clearance_required")
    if job.language_gate == "FAIL":
        reasons.append("language_requirement_failed")
    elif job.language_gate == "FLAG":
        warnings.append("language_requirement_flagged")
    if job.deadline is not None:
        try:
            deadline = date.fromisoformat(job.deadline)
        except ValueError:
            reasons.append("invalid_deadline")
        else:
            current = today or date.today()
            days_remaining = (deadline - current).days
            if days_remaining < 0:
                reasons.append("posting_expired")
            elif days_remaining <= 7:
                warnings.append("deadline_within_seven_days")
    if (
        job.compensation_min_jpy is not None
        and job.compensation_min_jpy < COMPENSATION_FLOOR_JPY
    ):
        reasons.append("compensation_below_floor")

    title = job.title.casefold()
    skills = {value.casefold() for value in job.skills}
    domains = {value.casefold() for value in job.domains}
    components = {
        "ai_skill": 30 if _has_ai_evidence(title, skills) else 0,
        "enterprise": 20 if skills & ENTERPRISE_SKILLS else 0,
        "consumer": 15 if skills & CONSUMER_SKILLS else 0,
        "location": 15 if job.japan_eligible else 0,
        "compensation": (
            5
            if job.compensation_min_jpy is None
            else 10
            if job.compensation_min_jpy >= COMPENSATION_TARGET_JPY
            else 7
            if job.compensation_min_jpy >= COMPENSATION_FLOOR_JPY
            else 0
        ),
        "mission": 10 if domains & PREFERRED_DOMAINS else 0,
    }
    score = sum(components.values())
    if score < AUTO_APPLY_THRESHOLD:
        reasons.append("score_below_threshold")
    return Evaluation(
        eligible=not reasons,
        score=score,
        components=components,
        reasons=tuple(reasons),
        warnings=tuple(warnings),
        language_gate=job.language_gate,
        language_note=job.language_note,
        deadline=job.deadline,
        strengths=tuple(job.strengths),
        gaps=tuple(job.gaps),
    )
