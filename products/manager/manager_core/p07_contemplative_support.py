"""Manager Core P07-3 -> P07-4 -> P07-5 -> P07-6 safe read-only integration.

This is a bounded product API *candidate builder*, not an executing agent:
- P07-3 COM-B is optional declared hypothesis, NOT inferred clinical causality.
- P07-4 offers opt-in tiny-action DRAFT_ONLY, reusing Habit Designer shape.
- P07-5 supplies consented observational features, never stages of insight.
- P07-6 harms and autonomy always OVERRIDE prompting and goal completion.
Never emits a network request, notification or clinical/spiritual assessment.
"""
from dataclasses import dataclass
from typing import Any, Literal, Mapping

from manager_core.p07_4_value_action_gate import SelfChosenGoal, plan_draft
from manager_core.p07_5_experience_observation import (
    ContemplativeObservation, observe_experience
)
from manager_core.p07_6_welfare_safety import OutcomeObservation, assess_welfare


@dataclass(frozen=True)
class ContemplativeSupportCandidate:
    status: Literal["NO_ACTION", "DRAFT_ONLY", "STOP", "STOP_AND_REFER"]
    reason: str
    draft: str | None = None
    comb_hypothesis_only: str = "UNKNOWN"
    observation_status: str = "NOT_USED"
    external_effects: tuple[str, ...] = ()
    model_inference_done: bool = False
    any_treatment_or_user_benefit_verified: bool = False


def propose_nonclinical_support(
    *,
    goal: SelfChosenGoal,
    experience: ContemplativeObservation,
    welfare: OutcomeObservation,
    hypothesized_comb: str = "UNKNOWN",
    existing_habit_designer_result: Mapping[str, Any] | None = None,
) -> ContemplativeSupportCandidate:
    """Compose the existing types without granting execution permissions.

    The caller must secure participant consent & privacy outside this module.
    The input from the model is untrusted even if its safety flag is false.
    """
    if hypothesized_comb not in ("Capability", "Opportunity", "Motivation", "UNKNOWN"):
        return ContemplativeSupportCandidate("NO_ACTION", "UNSUPPORTED_COM_B_CAUSAL_LABEL")
    # STOP always outranks a good-looking plan: protects burden and autonomy.
    welfare_check = assess_welfare(welfare)
    if welfare_check.status in ("STOP", "STOP_AND_REFER"):
        return ContemplativeSupportCandidate(
            welfare_check.status, welfare_check.reason,
            comb_hypothesis_only=hypothesized_comb,
            observation_status="STOP_OVERRIDE",
        )
    if welfare_check.status != "MEASURE_ONLY":
        return ContemplativeSupportCandidate(
            "NO_ACTION", welfare_check.reason,
            comb_hypothesis_only=hypothesized_comb,
        )
    observation_check = observe_experience(experience)
    if observation_check.status != "OBSERVATION_ONLY":
        status = ("STOP_AND_REFER"
                  if observation_check.status == "STOP_AND_REFER" else "NO_ACTION")
        return ContemplativeSupportCandidate(
            status, observation_check.reason,
            comb_hypothesis_only=hypothesized_comb,
            observation_status=observation_check.status,
        )
    draft = plan_draft(
        goal, existing_habit_designer_result=existing_habit_designer_result
    )
    return ContemplativeSupportCandidate(
        status=draft.choice,
        reason=draft.reason,
        draft=draft.draft,
        comb_hypothesis_only=hypothesized_comb,
        observation_status=observation_check.status,
        external_effects=(),
        model_inference_done=False,
        any_treatment_or_user_benefit_verified=False,
    )
