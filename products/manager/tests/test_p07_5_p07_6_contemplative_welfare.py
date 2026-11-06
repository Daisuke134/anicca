"""P07-5 and P07-6 SOFTWARE ONLY tests on synthetic case fixtures."""
import unittest
from manager_core.p07_5_experience_observation import (
    ContemplativeObservation, observe_experience
)
from manager_core.p07_6_welfare_safety import (
    OutcomeObservation, assess_welfare, score_who5_numeric,
    AssignedObservation, assigned_trial_audit,
)


def observation(**kwargs):
    d = dict(consent=True, revoked=False, domain="feeling_tone",
             reported_valence="unpleasant", urge_to_react_0to10=5,
             action_taken="pause", is_self_report=True)
    d.update(kwargs)
    return ContemplativeObservation(**d)


def outcome(**kwargs):
    d = dict(user_consented=True, consent_revoked=False,
             self_chosen_goal=True, goal_met=True,
             functioning_0to10=7, autonomy_0to10=8,
             burden_0to10=2, distress_0to10=1)
    d.update(kwargs)
    return OutcomeObservation(**d)


class P075InsightNonclassifierTests(unittest.TestCase):
    def test_observation_is_not_spiritual_attainment(self):
        r = observe_experience(observation())
        self.assertEqual(r.status, "OBSERVATION_ONLY")
        self.assertIn(("feeling_tone", "unpleasant"), r.aggregate_features)
        self.assertFalse(r.may_claim_enlightenment)
        self.assertFalse(r.may_claim_neural_marker)
        self.assertFalse(r.may_start_meditation)
        self.assertFalse(r.may_send_notification)
        self.assertFalse(r.causal_or_user_benefit_established)

    def test_no_silent_spiritual_classification(self):
        r = observe_experience(observation(asks_for_spiritual_attainment_label=True))
        self.assertEqual(r.status, "NO_ACTION")

    def test_no_unauthorized_practice(self):
        for case in (dict(consent=False), dict(revoked=True),
                     dict(is_self_report=False)):
            self.assertEqual(observe_experience(observation(**case)).status, "NO_ACTION")

    def test_intensive_practice_is_not_autonomously_supervised(self):
        for item in (dict(intensive_meditation_session=True),
                     dict(requested_duration_minutes=30)):
            self.assertEqual(observe_experience(observation(**item)).status, "NO_ACTION")

    def test_clinical_request_is_outside_scope(self):
        r = observe_experience(observation(asks_for_clinical_treatment=True))
        self.assertEqual(r.status, "STOP_AND_REFER")
        self.assertFalse(r.may_diagnose)

    def test_reactivity_range_checked(self):
        for x in (-1, 11, True, 1.5):
            self.assertEqual(observe_experience(
                observation(urge_to_react_0to10=x)).status, "NO_ACTION")

    def test_four_foundations_are_observation_domains(self):
        for domain in ("body", "feeling_tone", "mind_state", "dhamma_categories"):
            self.assertEqual(observe_experience(observation(domain=domain)).status,
                             "OBSERVATION_ONLY")

    def test_unknown_domain_rejected(self):
        self.assertEqual(observe_experience(observation(domain="stream_entry")).status,
                         "NO_ACTION")


class P076WelfareSafetyTests(unittest.TestCase):
    def test_consent_and_goals_first(self):
        for c in (dict(user_consented=False), dict(self_chosen_goal=False)):
            self.assertEqual(assess_welfare(outcome(**c)).status, "NO_ACTION")

    def test_stop_and_revoke_override(self):
        for c in (dict(requested_stop=True), dict(consent_revoked=True)):
            r = assess_welfare(outcome(**c))
            self.assertEqual(r.status, "STOP")
            self.assertFalse(r.may_continue_intervention)

    def test_any_reported_functioning_harm_pauses(self):
        for c in (dict(functional_impairment_reported=True),
                  dict(prolonged_impact_reported=True),
                  dict(sleep_disruption_reported=True),
                  dict(practice_was_intensive=True)):
            r = assess_welfare(outcome(**c))
            self.assertEqual(r.status, "STOP_AND_REFER")
            self.assertFalse(r.may_send_reminder)

    def test_unwanted_event_is_not_relabelled_insight_progress(self):
        r = assess_welfare(outcome(meditation_related_unwanted_experience=True))
        self.assertEqual(r.status, "STOP")
        self.assertFalse(r.causal_effect_established)

    def test_high_distress_pauses(self):
        r = assess_welfare(outcome(distress_0to10=9))
        self.assertEqual(r.status, "STOP_AND_REFER")

    def test_low_autonomy_pauses(self):
        r = assess_welfare(outcome(autonomy_0to10=1))
        self.assertEqual(r.status, "STOP")

    def test_high_burden_pauses(self):
        r = assess_welfare(outcome(burden_0to10=9))
        self.assertEqual(r.status, "STOP")

    def test_missing_goal_is_not_assumed_success(self):
        self.assertEqual(assess_welfare(outcome(goal_met=None)).status, "NO_ACTION")

    def test_invalid_ordinal_rejected(self):
        for score in (-1, 11, True, 0.8):
            self.assertEqual(assess_welfare(
                outcome(burden_0to10=score)).status, "NO_ACTION")

    def test_normal_report_is_only_descriptive(self):
        r = assess_welfare(outcome())
        self.assertEqual(r.status, "MEASURE_ONLY")
        self.assertFalse(r.causal_effect_established)
        self.assertFalse(r.clinical_recommendation)
        self.assertFalse(r.may_continue_intervention)
        self.assertEqual(r.score_kind, "UNVALIDATED_CUSTOM_MONITORING")

    def test_who5_rights_default_closed(self):
        with self.assertRaises(PermissionError):
            score_who5_numeric((5, 5, 5, 5, 5))

    def test_who5_numeric_scoring_research_with_rights(self):
        self.assertEqual(score_who5_numeric((0, 0, 0, 0, 0),
                                            rights_confirmed=True), 0)
        self.assertEqual(score_who5_numeric((5, 5, 5, 5, 5),
                                            rights_confirmed=True), 100)
        self.assertEqual(score_who5_numeric((0, 1, 2, 3, 4),
                                            rights_confirmed=True), 40)

    def test_who5_missing_invalid(self):
        for v in ((0, 1, 2, 3), (0, 1, 2, 3, None),
                  (0, 1, 2, 3, 6), [0, 1, 2, 3, 4]):
            with self.assertRaises(ValueError):
                score_who5_numeric(v, rights_confirmed=True)

    def test_trial_means_with_verified_assignment(self):
        rows = (
            AssignedObservation(0, 10, delivered=False),
            AssignedObservation(0, 20, delivered=True),
            AssignedObservation(1, 30, delivered=False),
            AssignedObservation(1, 40, delivered=True),
        )
        v = assigned_trial_audit(rows)
        self.assertEqual(v["arm1_minus_arm0"], 20)
        self.assertEqual(v["estimand_label"], "randomized_assignment_mean_difference")
        self.assertFalse(v["used_delivery_status_for_assignment"])
        self.assertFalse(v["causal_identification_claimed"])

    def test_missing_trial_outcome_never_called_itt(self):
        rows = (AssignedObservation(0, 10), AssignedObservation(0, None),
                AssignedObservation(1, 20), AssignedObservation(1, 25))
        v = assigned_trial_audit(rows)
        self.assertEqual(v["estimand_label"], "available_case_descriptive_NOT_ITT")
        self.assertEqual(v["missing_control"], 1)

    def test_invalid_assignment_rejected(self):
        rows = (AssignedObservation(True, 10), AssignedObservation(0, 10),
                AssignedObservation(1, 10), AssignedObservation(1, 10))
        with self.assertRaises(ValueError):
            assigned_trial_audit(rows)

    def test_no_metadata_exposes_individuals(self):
        result = assess_welfare(outcome())
        self.assertFalse(hasattr(result, "patient_id"))
        self.assertFalse(hasattr(result, "spiritual_stage"))
        self.assertFalse(hasattr(result, "clinical_diagnosis"))


if __name__ == "__main__":
    unittest.main()
