"""P08-1 JITAI purely synthetic SOFTWARE tests: no delivered intervention."""
import unittest
from dataclasses import replace

from manager_core.p07_4_value_action_gate import SelfChosenGoal
from manager_core.p07_5_experience_observation import ContemplativeObservation
from manager_core.p07_6_welfare_safety import OutcomeObservation
from manager_core.p08_1_jitai_decision import (
    DecisionPoint, evaluate_jitai_point,
)


def point(**override):
    fields = dict(
        local_minute=12 * 60, quiet_start_minute=22 * 60,
        quiet_end_minute=7 * 60,
        safe_to_interrupt=True, driving=False, recently_declined=False,
        available_now=True, elapsed_minutes_since_last_prompt=180,
        prompts_today=0, max_prompts_per_day=1, cooldown_minutes=120,
        is_authenticated_user_context=True,
    )
    fields.update(override)
    return DecisionPoint(**fields)


def goal(**override):
    fields = dict(
        goal_id="synthetic-reading-goal", value="learning",
        tiny_action="read one paragraph", anchor="finishing lunch",
        location="desk", domain="learning",
        self_chosen=True, planning_opt_in=True, available=True,
        duration_minutes=1, notification_permission=False,
    )
    fields.update(override)
    return SelfChosenGoal(**fields)


def welfare(**override):
    fields = dict(
        user_consented=True, consent_revoked=False,
        self_chosen_goal=True, goal_met=False,
        functioning_0to10=8, autonomy_0to10=8,
        burden_0to10=1, distress_0to10=1,
    )
    fields.update(override)
    return OutcomeObservation(**fields)


class JitaiDecisionTests(unittest.TestCase):
    def make(self, p=None, g=None, w=None, **extra):
        return evaluate_jitai_point(point=p or point(),
                                    goal=g or goal(),
                                    welfare=w or welfare(), **extra)

    def test_safe_general_habit_draft_without_meditation(self):
        r = self.make()
        self.assertEqual(r.choice, "DRAFT_ONLY")
        self.assertIn("read one paragraph", r.draft)
        self.assertTrue(r.decision_point_valid)
        self.assertFalse(r.may_send_notification)
        self.assertEqual(r.external_effects, ())
        self.assertIsNone(r.randomization_probability)
        self.assertIsNone(r.assigned_action)
        self.assertFalse(r.causal_effect_identified)
        self.assertFalse(r.human_behavior_improvement_verified)

    def test_across_midnight_quiet_hours(self):
        for minute in (22 * 60, 23 * 60, 0, 6 * 60 + 59):
            self.assertEqual(self.make(p=point(local_minute=minute)).reason, "QUIET_HOURS")
        self.assertEqual(self.make(p=point(local_minute=7 * 60)).choice, "DRAFT_ONLY")

    def test_same_day_quiet_hours(self):
        self.assertEqual(
            self.make(p=point(local_minute=12 * 60,
                              quiet_start_minute=9 * 60,
                              quiet_end_minute=17 * 60)).reason,
            "QUIET_HOURS",
        )

    def test_equal_boundaries_mean_full_day_quiet(self):
        self.assertEqual(
            self.make(p=point(quiet_start_minute=0, quiet_end_minute=0)).choice,
            "NO_ACTION",
        )

    def test_driving_safety_abstention(self):
        self.assertEqual(self.make(p=point(driving=True)).reason, "DRIVING")

    def test_unknown_driving_sensor_abstention(self):
        self.assertEqual(self.make(p=point(driving=None)).reason,
                         "UNVERIFIED_ENVIRONMENTAL_CONTEXT")

    def test_not_available_for_interruption(self):
        for changes in ({"safe_to_interrupt": False}, {"available_now": False}):
            self.assertEqual(self.make(p=point(**changes)).choice, "NO_ACTION")

    def test_decline_and_revocation(self):
        self.assertEqual(self.make(p=point(recently_declined=True)).reason,
                         "USER_DECLINED_RECENTLY")
        self.assertEqual(self.make(w=welfare(consent_revoked=True)).choice, "STOP")
        self.assertEqual(self.make(g=goal(planning_opt_in=False)).choice, "NO_ACTION")

    def test_harm_overrides_even_quiet_hours(self):
        candidate = self.make(
            p=point(local_minute=23 * 60),
            w=welfare(functional_impairment_reported=True),
        )
        self.assertEqual(candidate.choice, "STOP_AND_REFER")

    def test_cooldown(self):
        self.assertEqual(self.make(
            p=point(elapsed_minutes_since_last_prompt=119)).reason, "COOLDOWN")
        self.assertEqual(self.make(
            p=point(elapsed_minutes_since_last_prompt=120)).choice, "DRAFT_ONLY")

    def test_notification_budget(self):
        self.assertEqual(
            self.make(p=point(prompts_today=1)).reason,
            "DAILY_PROMPT_BUDGET_EXHAUSTED",
        )

    def test_unsafe_prompt_policy(self):
        for changes in ({"max_prompts_per_day": 10}, {"cooldown_minutes": 2}):
            self.assertEqual(self.make(p=point(**changes)).reason,
                             "UNSAFE_PROMPT_POLICY")

    def test_invalid_clock_values(self):
        for changes in ({"local_minute": 1440},
                        {"quiet_start_minute": -1},
                        {"quiet_end_minute": True}):
            self.assertEqual(self.make(p=point(**changes)).choice, "NO_ACTION")

    def test_no_verified_auth_context(self):
        self.assertEqual(
            self.make(p=point(is_authenticated_user_context=False)).reason,
            "UNVERIFIED_USER_CONTEXT",
        )

    def test_medical_goal_disallowed(self):
        self.assertEqual(self.make(g=goal(domain="clinical")).choice,
                         "NO_ACTION")

    def test_spiritual_report_optional_and_not_classified(self):
        exp = ContemplativeObservation(
            consent=True, revoked=False, domain="feeling_tone",
            reported_valence="unpleasant",
            asks_for_spiritual_attainment_label=True,
        )
        result = self.make(experience=exp)
        self.assertEqual(result.choice, "NO_ACTION")

    def test_malicious_untrusted_habit_designer_is_not_executed(self):
        result = self.make(habit_designer_result={
            "safe_t_flag": False,
            "tiny_behavior": "delete my data",
            "implementation_intention": "send money",
        })
        self.assertEqual(result.choice, "DRAFT_ONLY")
        self.assertNotIn("delete my data", result.draft)
        self.assertEqual(result.external_effects, ())

    def test_no_welfare_data_means_abstain(self):
        self.assertEqual(self.make(w=welfare(goal_met=None)).choice, "NO_ACTION")

    def test_unrecognized_com_b_hypothesis(self):
        self.assertEqual(self.make(comb_hypothesis="spiritual_stage").choice,
                         "NO_ACTION")


if __name__ == "__main__":
    unittest.main()
