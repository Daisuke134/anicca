import unittest
from runtime.loop import lm_loop_run


class TeamHQReceiptTests(unittest.TestCase):
    def receipt(self, **extra):
        return dict(schema_version=1, kind="team_hq_result", owner_id="team-hq-work",
                    occurrence_id="occ-1", status="verified", channel_id="C12345678",
                    message_ts="1793622512.888169", task_id="task-1", **extra)

    def verify(self, value, owner="team-hq-work", entrypoint="bin/team-hq.py"):
        fn = getattr(lm_loop_run, "_verified_team_hq_result", None)
        self.assertTrue(callable(fn), "HQ official receipt boundary is missing")
        return fn(value, owner, "occ-1", entrypoint)

    def test_worker_receipt_is_enabled_at_runtime_boundary(self):
        self.assertTrue(lm_loop_run._effect_result_hint_allowed("team-hq-work", "bin/team-hq.py"))
        self.assertFalse(lm_loop_run._effect_result_hint_allowed("team-hq-receive", "bin/team-hq.py"))

    def test_exact_slack_receipt_is_verified(self):
        self.assertEqual(self.verify(self.receipt()),
                         ("verified", "slack://channels/C12345678/messages/1793622512.888169"))

    def test_no_task_has_explicit_no_effect_receipt(self):
        value = self.receipt(); value.update(status="no_effect", message_ts=None, task_id=None)
        self.assertEqual(self.verify(value)[0], "not_applicable")

    def test_other_owner_or_entrypoint_cannot_claim_receipt(self):
        self.assertIsNone(self.verify(self.receipt(), owner="sibling"))
        self.assertIsNone(self.verify(self.receipt(), entrypoint="bin/other.py"))

    def test_unverified_or_malformed_result_is_not_accepted(self):
        for field, invalid in [("status", "posted"), ("occurrence_id", "other"),
                               ("message_ts", "not-a-ts"), ("channel_id", "../secret"),
                               ("task_id", ""), ("schema_version", True)]:
            with self.subTest(field=field):
                value=self.receipt();value[field]=invalid
                self.assertIsNone(self.verify(value))
