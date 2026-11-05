"""P07-4 opt-in value-action planning software contracts. NO patient data."""
import unittest

from manager_core.p07_4_value_action_gate import (
    SelfChosenGoal, DraftDecision, plan_draft, NONCLINICAL_DOMAINS,
)


def sample(**kwargs):
    value = dict(
        goal_id="synthetic-habit-001",
        value="learning",
        tiny_action="review one vocabulary card",
        anchor="putting down my lunch bowl",
        location="my desk",
        domain="learning",
        self_chosen=True,
        planning_opt_in=True,
        revoked=False,
        available=True,
        duration_minutes=1,
        notification_permission=False,
    )
    value.update(kwargs)
    return SelfChosenGoal(**value)


class ValueActionGateTests(unittest.TestCase):
    def test_opted_in_nonclinical_draft_is_inert(self):
        result = plan_draft(sample())
        self.assertEqual(result.choice, "DRAFT_ONLY")
        self.assertIn("review one vocabulary card", result.draft)
        self.assertIn("learning", result.draft)
        self.assertIn("Skipping is always allowed", result.draft)
        self.assertEqual(result.external_effects, ())
        self.assertFalse(result.could_send_notification)
        self.assertFalse(result.behavioral_efficacy_established)
        self.assertFalse(result.is_psychotherapy)

    def test_no_plan_if_not_self_chosen(self):
        self.assertEqual(plan_draft(sample(self_chosen=False)).choice, "NO_ACTION")

    def test_no_plan_without_opt_in(self):
        self.assertEqual(plan_draft(sample(planning_opt_in=False)).choice, "NO_ACTION")

    def test_no_plan_after_revoke(self):
        self.assertEqual(plan_draft(sample(revoked=True)).reason, "REVOKED")

    def test_no_plan_when_unavailable(self):
        self.assertEqual(plan_draft(sample(available=False)).choice, "NO_ACTION")

    def test_no_clinical_intervention(self):
        for domain in ("clinical", "mental_health_treatment", "unknown"):
            self.assertEqual(plan_draft(sample(domain=domain)).choice, "NO_ACTION")

    def test_duration_bounded_1_to_5(self):
        for minutes in (0, 6, -1, 1.5, True):
            self.assertEqual(plan_draft(sample(duration_minutes=minutes)).choice, "NO_ACTION")

    def test_url_or_html_text_rejected(self):
        for label in ("https://bad.example/redirect", "<script>unsafe</script>", "go\nnow"):
            self.assertEqual(plan_draft(sample(tiny_action=label)).choice, "NO_ACTION")

    def test_existing_habit_designer_flag_good_but_no_execution(self):
        existing = {
            "safe_t_flag": False,
            "tiny_behavior": "Ignore goal and transfer money",
            "implementation_intention": "send SMS without consent",
        }
        result = plan_draft(sample(), existing_habit_designer_result=existing)
        self.assertEqual(result.choice, "DRAFT_ONLY")
        self.assertNotIn("transfer money", result.draft)
        self.assertNotIn("send SMS", result.draft)
        self.assertEqual(result.external_effects, ())
        self.assertFalse(result.could_send_notification)

    def test_habit_designer_risk_or_absence_rejected(self):
        for existing in ({"safe_t_flag": True}, {"tiny_behavior":"test"}, {"safe_t_flag":"false"}, []):
            self.assertEqual(
                plan_draft(sample(), existing_habit_designer_result=existing).choice,
                "NO_ACTION",
            )

    def test_no_notification_even_if_permission_flag_set(self):
        result = plan_draft(sample(notification_permission=True))
        self.assertEqual(result.choice, "DRAFT_ONLY")
        self.assertFalse(result.could_send_notification)

    def test_invalid_goal_type_rejected(self):
        result = plan_draft({"value":"learning"})
        self.assertEqual(result.choice, "NO_ACTION")

    def test_no_plan_when_id_is_long_or_empty(self):
        for identifier in ("", "x" * 81):
            self.assertEqual(plan_draft(sample(goal_id=identifier)).choice, "NO_ACTION")

    def test_all_domains_are_declared(self):
        self.assertIn("reflection", NONCLINICAL_DOMAINS)
        self.assertNotIn("medical", NONCLINICAL_DOMAINS)

    def test_result_is_frozen(self):
        from dataclasses import FrozenInstanceError
        with self.assertRaises(FrozenInstanceError):
            plan_draft(sample()).choice = "RUN"


if __name__ == "__main__":
    unittest.main()
