"""P07-5: contemplative-experience observation CONTRACT, not an insight classifier.

This code operationalizes opt-in, narrow experience sampling while refusing to
infer awakening, Buddhist attainment, stages of insight, or neural mechanisms.
No meditation advice, diagnosis, network action, or individual data persistence.

References: MN10 four satipatthanas; SN22.59 nonself; SN12.2 dependent
origination; Yang et al. NeuroImage 2024 7T SoI n=1 case study.
"""
from dataclasses import dataclass
from typing import Literal

DOMAIN = frozenset({"body", "feeling_tone", "mind_state", "dhamma_categories"})
VALENCE = frozenset({"pleasant", "unpleasant", "neutral", "unsure"})
# Valence is the reported *hedonic tone* of feeling, not a clinical mood score.


@dataclass(frozen=True)
class ContemplativeObservation:
    """One non-identifying self-report, never an objective spiritual assessment."""
    consent: bool
    revoked: bool
    domain: str
    reported_valence: str
    urge_to_react_0to10: int | None = None
    action_taken: Literal["pause", "habitual_action", "alternative_action", "unknown"] = "unknown"
    is_self_report: bool = True
    intensive_meditation_session: bool = False
    asks_for_spiritual_attainment_label: bool = False
    asks_for_clinical_treatment: bool = False
    requested_duration_minutes: int = 0


@dataclass(frozen=True)
class ObservationDecision:
    status: Literal["NO_ACTION", "OBSERVATION_ONLY", "STOP_AND_REFER"]
    reason: str
    aggregate_features: tuple[tuple[str, str | int], ...] = ()
    may_start_meditation: bool = False
    may_send_notification: bool = False
    may_diagnose: bool = False
    may_claim_enlightenment: bool = False
    may_claim_neural_marker: bool = False
    causal_or_user_benefit_established: bool = False


def observe_experience(item: ContemplativeObservation) -> ObservationDecision:
    """Return a hypothetical anonymized observation only when consented.

    This method intentionally does not store results or automatically act.
    Reports of impairment or distress belong to the P07-6 safety module,
    *before* any plan or intervention is presented to a user.
    """
    def no(reason: str, status: Literal["NO_ACTION", "STOP_AND_REFER"] = "NO_ACTION"):
        return ObservationDecision(status=status, reason=reason)

    if type(item) is not ContemplativeObservation:
        return no("INVALID_EXPERIENCE_REPORT")
    if item.revoked is True:
        return no("CONSENT_REVOKED")
    if item.consent is not True or item.is_self_report is not True:
        return no("NO_SELF_REPORT_PERMISSION")
    if item.asks_for_clinical_treatment is True:
        return no("OUT_OF_SCOPE_CLINICAL", "STOP_AND_REFER")
    if item.asks_for_spiritual_attainment_label is True:
        return no("AWAKENING_OR_INSIGHT_STAGE_NOT_CLASSIFIABLE")
    if item.intensive_meditation_session is True or item.requested_duration_minutes > 20:
        return no("INTENSIVE_PRACTICE_REQUIRES_SEPARATE_HUMAN_LED_SAFETY_REVIEW")
    if type(item.requested_duration_minutes) is not int or item.requested_duration_minutes < 0:
        return no("INVALID_PRACTICE_DURATION")
    if item.domain not in DOMAIN or item.reported_valence not in VALENCE:
        return no("UNSUPPORTED_SATIPATTHANA_OBSERVATION")
    score = item.urge_to_react_0to10
    if score is not None and (type(score) is not int or not 0 <= score <= 10):
        return no("INVALID_REACTIVITY_SCORE")
    if item.action_taken not in ("pause", "habitual_action", "alternative_action", "unknown"):
        return no("INVALID_ACTION_CODE")
    aggregate = [
        ("domain", item.domain),
        ("feeling_tone", item.reported_valence),
        ("observed_action", item.action_taken),
    ]
    if score is not None:
        aggregate.append(("reported_urge_0to10", score))
    return ObservationDecision(
        "OBSERVATION_ONLY",
        "SELF_REPORTED_NONCLINICAL_FEATURES_NO_SPIRITUAL_DIAGNOSIS",
        aggregate_features=tuple(aggregate),
    )
