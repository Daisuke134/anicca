"""Manager P08-1: Just-in-Time Adaptive Intervention (JITAI) READ-ONLY gate.

Extends pre-existing P07-4/5/6 contracts instead of copying their science
or inventing a new intervention engine.

This ONLY selects a draft candidate or abstention. NO notification, no paid
action, no external I/O, no random assignment, no logged participant records,
no clinical or spiritual advice, and NO efficacy claim.

Primary JITAI references:
Nahum-Shani et al. (2018), DOI 10.1007/s12160-016-9830-8.
Klasnja et al. (2019), HeartSteps, DOI 10.1093/abm/kay067.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping, Any

from manager_core.p07_4_value_action_gate import SelfChosenGoal, plan_draft
from manager_core.p07_5_experience_observation import ContemplativeObservation
from manager_core.p07_6_welfare_safety import OutcomeObservation, assess_welfare
from manager_core.p07_contemplative_support import propose_nonclinical_support


@dataclass(frozen=True)
class DecisionPoint:
    """Predecision context; no personal identifiers or future outcomes.

    Times are intentionally minutes of user-local day, not system UTC.
    A later execution boundary must verify IANA timezone, DST, actual
    consent and a trusted source of device context independently.
    """
    local_minute: int
    quiet_start_minute: int
    quiet_end_minute: int
    safe_to_interrupt: bool
    driving: bool
    recently_declined: bool
    available_now: bool
    elapsed_minutes_since_last_prompt: int | None
    prompts_today: int
    max_prompts_per_day: int = 1
    cooldown_minutes: int = 120
    is_authenticated_user_context: bool = False


@dataclass(frozen=True)
class JitaiCandidate:
    """Pure decision receipt, with NO power to deliver or run an intervention."""
    choice: Literal["NO_ACTION", "DRAFT_ONLY", "STOP", "STOP_AND_REFER"]
    reason: str
    draft: str | None = None
    source: str = "RULES_P08_1_P07_SAFETY"
    decision_point_valid: bool = False
    assigned_action: None = None
    randomization_probability: None = None
    causal_effect_identified: bool = False
    human_behavior_improvement_verified: bool = False
    may_send_notification: bool = False
    external_effects: tuple[str, ...] = ()


def _in_quiet_hours(minute: int, start: int, end: int) -> bool:
    """Support both same-day and across-midnight quiet intervals."""
    if start == end:  # explicit conservative choice: all day is quiet
        return True
    if start < end:
        return start <= minute < end
    return minute >= start or minute < end


def evaluate_jitai_point(
    *,
    point: DecisionPoint,
    goal: SelfChosenGoal,
    experience: ContemplativeObservation | None = None,
    welfare: OutcomeObservation,
    comb_hypothesis: str = "UNKNOWN",
    habit_designer_result: Mapping[str, Any] | None = None,
) -> JitaiCandidate:
    """Select a candidate only at a legitimately safe decision point.

    P07-6 harm/revocation check is always FIRST, even during quiet hours.
    An opted-in nonclinical plan returns DRAFT_ONLY, not a delivered message.
    Never interpret a model's estimated probability as the causal effect of
    intervening. No actual MRT randomization occurs in P08-1.
    """
    def no(reason: str) -> JitaiCandidate:
        return JitaiCandidate("NO_ACTION", reason)

    if type(welfare) is not OutcomeObservation:
        return no("INVALID_WELFARE_INPUT")
    safety = assess_welfare(welfare)
    if safety.status in ("STOP", "STOP_AND_REFER"):
        return JitaiCandidate(safety.status, safety.reason)
    if safety.status != "MEASURE_ONLY":
        return no("NO_VALID_CONSENTED_WELFARE_CONTEXT")

    if type(point) is not DecisionPoint:
        return no("INVALID_DECISION_POINT")
    checks = (
        point.local_minute,
        point.quiet_start_minute,
        point.quiet_end_minute,
    )
    if any(type(t) is not int or not 0 <= t < 1440 for t in checks):
        return no("INVALID_LOCAL_TIME")
    if type(point.is_authenticated_user_context) is not bool or point.is_authenticated_user_context is not True:
        return no("UNVERIFIED_USER_CONTEXT")
    if any(type(v) is not bool for v in (point.driving,point.safe_to_interrupt,
                                         point.available_now,point.recently_declined)):
        return no("UNVERIFIED_ENVIRONMENTAL_CONTEXT")
    if point.driving is True:
        return no("DRIVING")
    if point.safe_to_interrupt is not True or point.available_now is not True:
        return no("NOT_RECEPTIVE_OR_UNAVAILABLE")
    if point.recently_declined is True:
        return no("USER_DECLINED_RECENTLY")
    if _in_quiet_hours(point.local_minute,
                       point.quiet_start_minute,
                       point.quiet_end_minute):
        return no("QUIET_HOURS")
    integers = (point.prompts_today, point.max_prompts_per_day,
                point.cooldown_minutes)
    if any(type(x) is not int or x < 0 for x in integers):
        return no("INVALID_PROMPT_BUDGET")
    if point.max_prompts_per_day > 3 or point.cooldown_minutes < 30:
        return no("UNSAFE_PROMPT_POLICY")
    if point.prompts_today >= point.max_prompts_per_day:
        return no("DAILY_PROMPT_BUDGET_EXHAUSTED")
    elapsed = point.elapsed_minutes_since_last_prompt
    if elapsed is None and point.prompts_today > 0:
        return no("UNKNOWN_COOLDOWN_HISTORY")
    if elapsed is not None:
        if type(elapsed) is not int or elapsed < 0:
            return no("INVALID_ELAPSED_TIME")
        if elapsed < point.cooldown_minutes:
            return no("COOLDOWN")

    # Ordinary JITAI goals do not require contemplative experience reports.
    # Reuse the four-layer P07 contract when a report was explicitly provided.
    if experience is None:
        if comb_hypothesis not in ("Capability", "Opportunity", "Motivation", "UNKNOWN"):
            return no("UNSUPPORTED_COM_B_CAUSAL_LABEL")
        plan = plan_draft(goal, existing_habit_designer_result=habit_designer_result)
        choice, reason, content = plan.choice, plan.reason, plan.draft
    else:
        outcome = propose_nonclinical_support(
            goal=goal,
            experience=experience,
            welfare=welfare,
            hypothesized_comb=comb_hypothesis,
            existing_habit_designer_result=habit_designer_result,
        )
        choice, reason, content = outcome.status, outcome.reason, outcome.draft
    return JitaiCandidate(
        choice=choice,
        reason=reason,
        draft=content if choice == "DRAFT_ONLY" else None,
        decision_point_valid=True,
        may_send_notification=False,
        external_effects=(),
    )
