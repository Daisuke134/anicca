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
        self.assertTrue(lm_loop_run._effect_result_hint_allowed("team-hq-receive", "bin/team-hq.py"))

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


class TeamHQReasonReceiptTests(unittest.TestCase):
    def value(self):
        return dict(schema_version=1, kind="team_hq_reason_receive_result",
                    owner_id="team-hq-receive", occurrence_id="occ-1",
                    status="verified", message_ids=["01M6G11XSHQTVE7JPSSAEE34JA"])

    def verify(self, value, owner="team-hq-receive", entrypoint="bin/team-hq.py"):
        fn = getattr(lm_loop_run, "_verified_team_hq_reason_result", None)
        self.assertTrue(callable(fn), "Reason receiver receipt boundary missing")
        return fn(value, owner, "occ-1", entrypoint)

    def test_provider_message_ids_are_accepted_only_for_receiver(self):
        self.assertEqual(self.verify(self.value()),
                         ("verified", "reason://messages/01M6G11XSHQTVE7JPSSAEE34JA"))
        self.assertIsNone(self.verify(self.value(), owner="team-hq-work"))
        self.assertIsNone(self.verify(self.value(), entrypoint="bin/other.py"))

    def test_idle_is_explicit_and_cannot_hide_sent_messages(self):
        value=self.value();value.update(status="no_effect", message_ids=[])
        self.assertEqual(self.verify(value)[0], "not_applicable")
        value["message_ids"]=["01M6G11XSHQTVE7JPSSAEE34JA"]
        self.assertIsNone(self.verify(value))

    def test_malformed_or_cross_occurrence_receipt_is_rejected(self):
        for field, invalid in [("status", "posted"), ("occurrence_id", "other"),
                               ("owner_id", "other"), ("schema_version", True),
                               ("message_ids", []), ("message_ids", ["../secret"]),
                               ("message_ids", "01M6G11XSHQTVE7JPSSAEE34JA")]:
            with self.subTest(field=field, invalid=invalid):
                value=self.value();value[field]=invalid
                self.assertIsNone(self.verify(value))
