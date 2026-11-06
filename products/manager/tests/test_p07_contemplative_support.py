"""P07 unified safe candidate builder contract: synthetic data, zero effects."""
import unittest

from manager_core.p07_4_value_action_gate import SelfChosenGoal
from manager_core.p07_5_experience_observation import ContemplativeObservation
from manager_core.p07_6_welfare_safety import OutcomeObservation
from manager_core.p07_contemplative_support import propose_nonclinical_support


def goal(**kwargs):
    d = dict(goal_id="synthetic-001", value="learning",
             tiny_action="read one paragraph",
             anchor="finishing lunch", location="my desk",
             domain="learning", self_chosen=True,
             planning_opt_in=True, available=True, duration_minutes=1)
    d.update(kwargs)
    return SelfChosenGoal(**d)


def exp(**kwargs):
    d = dict(consent=True, revoked=False, domain="feeling_tone",
             reported_valence="neutral")
    d.update(kwargs)
    return ContemplativeObservation(**d)


def wellbeing(**kwargs):
    d = dict(user_consented=True, consent_revoked=False,
             self_chosen_goal=True, goal_met=False,
             autonomy_0to10=8, burden_0to10=1,
             distress_0to10=1)
    d.update(kwargs)
    return OutcomeObservation(**d)


class CombinedP07SafetyTests(unittest.TestCase):
    def test_safe_nonclinical_plan_is_never_executed(self):
        p = propose_nonclinical_support(goal=goal(), experience=exp(),
                welfare=wellbeing(), hypothesized_comb="Opportunity")
        self.assertEqual(p.status, "DRAFT_ONLY")
        self.assertEqual(p.observation_status, "OBSERVATION_ONLY")
        self.assertEqual(p.comb_hypothesis_only, "Opportunity")
        self.assertFalse(p.model_inference_done)
        self.assertFalse(p.any_treatment_or_user_benefit_verified)
        self.assertEqual(p.external_effects, ())

    def test_welfare_harm_overrides_value_plan(self):
        p = propose_nonclinical_support(goal=goal(),experience=exp(),
                welfare=wellbeing(functional_impairment_reported=True))
        self.assertEqual(p.status, "STOP_AND_REFER")
        self.assertIsNone(p.draft)

    def test_autonomy_harm_overrides_value_plan(self):
        p = propose_nonclinical_support(goal=goal(),experience=exp(),
                welfare=wellbeing(autonomy_0to10=1))
        self.assertEqual(p.status, "STOP")

    def test_user_revocation_overrides_all(self):
        p = propose_nonclinical_support(goal=goal(),experience=exp(),
                welfare=wellbeing(consent_revoked=True))
        self.assertEqual(p.status, "STOP")

    def test_no_unconsented_insight_observation(self):
        p = propose_nonclinical_support(goal=goal(),experience=exp(consent=False),
                welfare=wellbeing())
        self.assertEqual(p.status, "NO_ACTION")

    def test_never_assert_spiritual_stage(self):
        p = propose_nonclinical_support(goal=goal(),
                experience=exp(asks_for_spiritual_attainment_label=True),
                welfare=wellbeing())
        self.assertEqual(p.status, "NO_ACTION")

    def test_no_unknown_comb_domain(self):
        p = propose_nonclinical_support(goal=goal(),experience=exp(),
                welfare=wellbeing(), hypothesized_comb="past_life_karma")
        self.assertEqual(p.status, "NO_ACTION")

    def test_bad_existing_habit_designer_halts(self):
        p = propose_nonclinical_support(goal=goal(),experience=exp(),
                welfare=wellbeing(),
                existing_habit_designer_result={"safe_t_flag":True})
        self.assertEqual(p.status, "NO_ACTION")

    def test_model_generated_malicious_behavior_not_used(self):
        p = propose_nonclinical_support(goal=goal(),experience=exp(),
                welfare=wellbeing(),
                existing_habit_designer_result={
                    "safe_t_flag":False,
                    "tiny_behavior":"delete all emails",
                    "implementation_intention":"run financial transaction"
                })
        self.assertEqual(p.status, "DRAFT_ONLY")
        self.assertNotIn("delete all emails", p.draft)
        self.assertNotIn("financial transaction", p.draft)
        self.assertEqual(p.external_effects, ())

    def test_absent_goal_outcome_is_not_caused_by_ai(self):
        p = propose_nonclinical_support(goal=goal(),experience=exp(),
                welfare=wellbeing(goal_met=None))
        self.assertEqual(p.status, "NO_ACTION")


if __name__ == "__main__":
    unittest.main()
