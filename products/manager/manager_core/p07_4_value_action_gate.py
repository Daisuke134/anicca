"""P07-4: value-aligned non-clinical action-plan draft gate for Manager.

Accepts the shape of the existing x402 habit-designer *only as untrusted input*.
This adapter does not implement CBT/ACT therapy, diagnose mental illness, call an
LLM, send a reminder, or exercise any provider authority.

Evidence behind ACT psychological flexibility does not validate this software
gate, nor imply a demonstrated improvement in users' lives.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import re

NONCLINICAL_DOMAINS = frozenset({
    "learning", "organization", "creative_practice", "light_activity",
    "reflection", "social_connection",
})
_ALLOWED_SAFE_KEYS = frozenset({"tiny_behavior", "implementation_intention", "safe_t_flag"})
_CONTROL = re.compile(r"[\x00-\x1F\x7F-\x9F]")
_URL = re.compile(r"(?:https?://|www\.)", re.IGNORECASE)


@dataclass(frozen=True)
class SelfChosenGoal:
    """Explicit self-chosen goal, not an inferred diagnosis or a hidden preference."""
    goal_id: str
    value: str
    tiny_action: str
    anchor: str
    location: str
    domain: str
    self_chosen: bool = False
    planning_opt_in: bool = False
    revoked: bool = False
    available: bool = False
    duration_minutes: int = 1
    notification_permission: bool = False


@dataclass(frozen=True)
class DraftDecision:
    """NO_ACTION or an inert read-only plan; never an authorization to execute."""
    choice: str
    reason: str
    draft: str | None = None
    external_effects: tuple[str, ...] = ()
    could_send_notification: bool = False
    is_psychotherapy: bool = False
    behavioral_efficacy_established: bool = False


def _bounded_text(text: Any, maximum: int) -> bool:
    return (
        type(text) is str
        and 1 <= len(text.strip()) <= maximum
        and not _CONTROL.search(text)
        and not _URL.search(text)
        and "<" not in text and ">" not in text
    )


def plan_draft(
    grant: SelfChosenGoal,
    *,
    existing_habit_designer_result: Mapping[str, Any] | None = None,
) -> DraftDecision:
    """Return only an inert plan for a value the person explicitly selected.

    Reuses the extant habit designer's safe_t_flag as one *additional* fail-closed
    signal, never as clinical certification and never as permission to act.
    The person's own action and anchor, not untrusted LLM text, are authoritative.
    """
    def no(reason: str) -> DraftDecision:
        return DraftDecision(choice="NO_ACTION", reason=reason)

    if type(grant) is not SelfChosenGoal:
        return no("INVALID_GRANT")
    if (grant.self_chosen is not True or grant.planning_opt_in is not True):
        return no("NO_EXPLICIT_SELF_CHOSEN_GOAL_OR_PLAN_CONSENT")
    if grant.revoked is True:
        return no("REVOKED")
    if grant.available is not True:
        return no("NOT_AVAILABLE")
    if grant.domain not in NONCLINICAL_DOMAINS:
        return no("OUT_OF_SCOPE_OR_CLINICAL")
    if type(grant.duration_minutes) is not int or not 1 <= grant.duration_minutes <= 5:
        return no("INVALID_SMALL_STEP_DURATION")
    if not all([
        _bounded_text(grant.goal_id, 80),
        _bounded_text(grant.value, 120),
        _bounded_text(grant.tiny_action, 180),
        _bounded_text(grant.anchor, 100),
        _bounded_text(grant.location, 100),
    ]):
        return no("UNSAFE_OR_INVALID_TEXT")

    if existing_habit_designer_result is not None:
        if not isinstance(existing_habit_designer_result, Mapping):
            return no("INVALID_HABIT_DESIGNER_RESULT")
        if existing_habit_designer_result.get("safe_t_flag") is not False:
            return no("UNVERIFIED_OR_RISK_FLAGGED_EXISTING_DESIGNER_OUTPUT")
        # A model-produced plan may be useful as a hypothesis, but is not copied
        # into a read-only user-facing action without further safety review.
        # This adapter intentionally ignores proposed untrusted action text.

    draft = (
        f"After {grant.anchor}, in {grant.location}, I can choose to "
        f"{grant.tiny_action} for up to {grant.duration_minutes} minute(s), "
        f"because I value {grant.value}. Skipping is always allowed."
    )
    return DraftDecision(
        choice="DRAFT_ONLY",
        reason="EXPLICIT_NONCLINICAL_CONSENTED_SMALL_STEP",
        draft=draft,
        external_effects=(),
        could_send_notification=False,
        is_psychotherapy=False,
        behavioral_efficacy_established=False,
    )
