"""P07-6: safe *measurement* of user-chosen outcomes, autonomy and harms.

This is not psychotherapy, a validated wellbeing scale, or a medical device.
No scheduled action, contact with third parties, stored individual answers,
retreat coaching, diagnosis, or automatic efficacy claims.

The numeric 0..10 input is an *unvalidated internal monitoring format*, NOT
a replacement for licensed WHO-5, WHOQOL-BREF, PROMIS, FFMQ or MedEx-I.
Use validated scales ONLY with applicable commercial rights and exact versions.
"""
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class OutcomeObservation:
    user_consented: bool
    consent_revoked: bool
    self_chosen_goal: bool
    goal_met: bool | None
    functioning_0to10: int | None = None
    autonomy_0to10: int | None = None
    burden_0to10: int | None = None
    distress_0to10: int | None = None
    meditation_related_unwanted_experience: bool = False
    functional_impairment_reported: bool = False
    sleep_disruption_reported: bool = False
    prolonged_impact_reported: bool = False
    requested_stop: bool = False
    severe_safety_concern: bool = False
    practice_was_intensive: bool = False


@dataclass(frozen=True)
class WelfareDecision:
    status: Literal["NO_ACTION", "MEASURE_ONLY", "STOP", "STOP_AND_REFER"]
    reason: str
    may_continue_intervention: bool = False
    may_send_reminder: bool = False
    causal_effect_established: bool = False
    clinical_recommendation: bool = False
    score_kind: str = "UNVALIDATED_CUSTOM_MONITORING"
    notes: tuple[str, ...] = ()


def _valid_ordinal(value: int | None) -> bool:
    return value is None or (type(value) is int and 0 <= value <= 10)


def assess_welfare(item: OutcomeObservation) -> WelfareDecision:
    """Fail closed on revocation or harm, abstain on missing/uncertain outcome.

    Negative effects must not be re-labelled as 'insight progress'.
    The system can stop its own nonclinical assistance, but must not claim
    a professional reviewed the report or autonomously treat it.
    """
    no = lambda reason: WelfareDecision("NO_ACTION", reason)
    if type(item) is not OutcomeObservation:
        return no("INVALID_REPORT")
    if item.requested_stop is True or item.consent_revoked is True:
        return WelfareDecision("STOP", "USER_CHOSE_TO_STOP")
    if item.user_consented is not True or item.self_chosen_goal is not True:
        return no("NO_SELF_CHOSEN_GOAL_OR_CONSENT")
    if item.severe_safety_concern is True:
        return WelfareDecision(
            "STOP_AND_REFER", "REPORTED_SEVERE_SAFETY_CONCERN",
            notes=("Stop nonclinical intervention.",
                   "Present appropriate local emergency/professional support options; no automatic contact."),
        )
    if (item.functional_impairment_reported is True
            or item.prolonged_impact_reported is True
            or item.sleep_disruption_reported is True):
        return WelfareDecision(
            "STOP_AND_REFER", "POTENTIALLY_IMPAIRING_MEDITATION_RELATED_EVENT",
            notes=("Do not intensify meditation or assert symptoms mean progress.",
                   "Offer a stop and appropriate independent professional support options."),
        )
    if item.practice_was_intensive is True:
        return WelfareDecision(
            "STOP_AND_REFER", "INTENSIVE_PRACTICE_OUTSIDE_AUTONOMOUS_SCOPE",
            notes=("Do not automatically supervise intensive retreats.",),
        )
    if not all(_valid_ordinal(v) for v in (
        item.functioning_0to10,
        item.autonomy_0to10,
        item.burden_0to10,
        item.distress_0to10,
    )):
        return no("INVALID_UNVALIDATED_MONITORING_SCORE")
    if item.goal_met is None:
        return no("NO_MEASURED_GOAL_OUTCOME")
    if type(item.goal_met) is not bool:
        return no("INVALID_GOAL_OUTCOME_TYPE")
    # Short-term and nonimpairing unwanted experiences still count as potential
    # harm. A monitor is not entitled to dismiss or normalize them.
    if item.meditation_related_unwanted_experience is True:
        return WelfareDecision(
            "STOP", "MEDITATION_RELATED_UNWANTED_EXPERIENCE_REPORTED",
            notes=("Ask for opt-in reassessment only after the participant is ready.",),
        )
    if item.distress_0to10 is not None and item.distress_0to10 >= 8:
        return WelfareDecision(
            "STOP_AND_REFER", "HIGH_SELF_REPORTED_DISTRESS",
            notes=("Stop pressure and offer nonautomated support options.",),
        )
    if item.autonomy_0to10 is not None and item.autonomy_0to10 <= 2:
        return WelfareDecision(
            "STOP", "LOW_REPORTED_AUTONOMY",
            notes=("Provide a clear opt-out path; do not optimize for compliance.",),
        )
    if item.burden_0to10 is not None and item.burden_0to10 >= 8:
        return WelfareDecision(
            "STOP", "HIGH_REPORTED_INTERVENTION_BURDEN",
            notes=("Reduce pressure; no guilt/friction nudges.",),
        )
    return WelfareDecision(
        "MEASURE_ONLY",
        "DESCRIPTIVE_ONE_TIME_REPORT_NO_COUNTERFACTUAL",
        notes=("Do not call one user's before/after change a causal effect.",
               "If a measure has no licensed/validated questionnaire, label it exploratory."),
    )


def score_who5_numeric(
    five_0to5_responses: tuple[int, ...],
    *,
    rights_confirmed: bool = False,
) -> int:
    """Arithmetic scoring ONLY, no WHO copyrighted questionnaire text.

    The WHO 2024 published questionnaire is CC BY-NC-SA 3.0 IGO.
    Do not use it in a commercial service without suitable authorization.
    WHO and OECD specify raw sum 0..25, multiply by 4 => 0..100.
    A missing item invalidates the total; it is not silently imputed.
    """
    if rights_confirmed is not True:
        raise PermissionError("WHO-5 commercial usage rights not confirmed")
    if not isinstance(five_0to5_responses, tuple) or len(five_0to5_responses) != 5:
        raise ValueError("WHO-5 arithmetic requires exactly five values")
    if any(type(x) is not int or not 0 <= x <= 5 for x in five_0to5_responses):
        raise ValueError("WHO-5 response values 0..5; no missing-item imputation")
    return 4 * sum(five_0to5_responses)


@dataclass(frozen=True)
class AssignedObservation:
    """For a separate controlled research study, not default production data."""
    assigned_arm: int  # 0 control or 1 intervention at *randomization*
    outcome: float | None  # fixed outcome, same direction and horizon across arms
    delivered: bool | None = None  # NEVER use delivery status as ITT assignment


def assigned_trial_audit(rows: tuple[AssignedObservation, ...]) -> dict:
    """Only score group contrasts; never relabel corrected 'send' as randomized.

    This is an educational statistical boundary, not a prespecified study
    analysis, treatment authorization, individual CATE or clinical claim.
    """
    if not isinstance(rows, tuple) or len(rows) < 4:
        raise ValueError("trial rows must be a tuple with >=4 records")
    groups = {0: [], 1: []}
    n_assigned = {0: 0, 1: 0}
    n_missing = {0: 0, 1: 0}
    for r in rows:
        if type(r) is not AssignedObservation or type(r.assigned_arm) is not int:
            raise ValueError("assignment must be verified at randomization")
        if r.assigned_arm not in groups:
            raise ValueError("arm must be 0 or 1")
        n_assigned[r.assigned_arm] += 1
        if r.outcome is None:
            n_missing[r.assigned_arm] += 1
        elif (type(r.outcome) not in (float, int)
              or not __import__("math").isfinite(r.outcome)):
            raise ValueError("invalid observed outcome")
        else:
            groups[r.assigned_arm].append(float(r.outcome))
    if not groups[0] or not groups[1]:
        raise ValueError("both arms need outcomes")
    means = {k: sum(v) / len(v) for k, v in groups.items()}
    # With missing outcomes this contrast is only an available-case description.
    complete = (n_missing[0] + n_missing[1] == 0)
    return {
        "allocation_basis": "original_randomized_assignment_NOT_delivery_status",
        "assigned_control": n_assigned[0], "assigned_intervention": n_assigned[1],
        "missing_control": n_missing[0], "missing_intervention": n_missing[1],
        "control_mean": means[0], "intervention_mean": means[1],
        "arm1_minus_arm0": means[1] - means[0],
        "outcome_missing": not complete,
        "estimand_label": "randomized_assignment_mean_difference"
        if complete else "available_case_descriptive_NOT_ITT",
        "causal_identification_claimed": False,  # no independent design review
        "manager_user_benefit_established": False,
        "used_delivery_status_for_assignment": False,
    }
