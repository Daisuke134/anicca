import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from job_search_loop.outbox import DeliveryUncertain
from job_search_loop.recruiter_reply import (
    ReplyError,
    build_approved_reply,
    is_safe_recruiter_message,
    send_reply_once,
)


class RecruiterReplyTests(unittest.TestCase):
    def setUp(self):
        self.profile = {
            "candidate": {
                "name": "Daisuke Narita",
                "application_email": "candidate@example.com",
                "phone": "09000000000",
                "base": "Tokyo, Japan",
                "desired_compensation_jpy": "JPY 7M–10M",
                "location_preferences": ["Tokyo", "remote from Japan"],
            },
            "facts": [
                {
                    "id": "mufg",
                    "claim": "Contributed to MUFG's production AI deployment.",
                    "evidence": "fixture",
                },
                {
                    "id": "anicca_consumer",
                    "claim": "Built and grew a consumer AI product.",
                    "evidence": "fixture",
                },
            ],
        }

    def test_experience_reply_contains_only_requested_approved_claims(self):
        decision = build_approved_reply(
            self.profile,
            question_kind="experience",
            question_source_span="Could you describe your enterprise AI experience?",
            fact_ids=["mufg", "anicca_consumer"],
        )
        self.assertEqual(decision["action"], "auto_reply")
        self.assertEqual(decision["fact_ids"], ["mufg", "anicca_consumer"])
        self.assertIn(self.profile["facts"][0]["claim"], decision["body"])
        self.assertIn(self.profile["facts"][1]["claim"], decision["body"])

    def test_profile_fields_can_answer_location_compensation_and_contact(self):
        location = build_approved_reply(
            self.profile,
            question_kind="location",
            question_source_span="Where are you based?",
        )
        compensation = build_approved_reply(
            self.profile,
            question_kind="desired_compensation",
            question_source_span="What compensation range are you seeking?",
        )
        contact = build_approved_reply(
            self.profile,
            question_kind="contact",
            question_source_span="What is the best phone number?",
        )
        self.assertIn("Tokyo, Japan", location["body"])
        self.assertIn("remote from Japan", location["body"])
        self.assertIn("JPY 7M–10M", compensation["body"])
        self.assertIn("09000000000", contact["body"])

    def test_unknown_private_or_legal_answers_are_blocked(self):
        for kind in (
            "work_authorization",
            "visa",
            "start_date",
            "current_compensation",
            "references",
            "legal",
        ):
            with self.subTest(kind=kind):
                decision = build_approved_reply(
                    self.profile,
                    question_kind=kind,
                    question_source_span="Please confirm.",
                )
                self.assertEqual(decision["action"], "blocked")
                self.assertNotIn("body", decision)

    def test_scheduling_routes_to_next_workflow_without_replying(self):
        decision = build_approved_reply(
            self.profile,
            question_kind="scheduling",
            question_source_span="Choose an interview time.",
        )
        self.assertEqual(decision["action"], "route_scheduling")
        self.assertNotIn("body", decision)

    def test_missing_fact_or_question_source_fails_closed(self):
        with self.assertRaisesRegex(ReplyError, "fact"):
            build_approved_reply(
                self.profile,
                question_kind="experience",
                question_source_span="Tell us more.",
                fact_ids=["invented"],
            )
        with self.assertRaisesRegex(ReplyError, "source"):
            build_approved_reply(
                self.profile,
                question_kind="location",
                question_source_span=" ",
            )

    def test_bulk_and_no_reply_messages_are_not_safe_recruiters(self):
        self.assertFalse(
            is_safe_recruiter_message(
                {"From": "noreply@example.com", "Auto-Submitted": "no"}
            )
        )
        self.assertFalse(
            is_safe_recruiter_message(
                {"From": "recruiter@example.com", "Precedence": "bulk"}
            )
        )
        self.assertFalse(
            is_safe_recruiter_message(
                {"From": "recruiter@example.com", "List-Id": "jobs.example.com"}
            )
        )
        self.assertTrue(
            is_safe_recruiter_message(
                {"From": "Recruiter <recruiter@example.com>", "Auto-Submitted": "no"}
            )
        )

    def test_send_reply_is_threaded_body_file_only_and_at_most_once(self):
        decision = build_approved_reply(
            self.profile,
            question_kind="location",
            question_source_span="Where are you based?",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            completed = type(
                "Completed",
                (),
                {
                    "returncode": 0,
                    "stdout": json.dumps(
                        {"messageId": "sent-message", "threadId": "thread-1"}
                    ),
                    "stderr": "",
                },
            )()
            with patch("subprocess.run", return_value=completed) as call:
                first = send_reply_once(
                    database=root / "outbox.sqlite3",
                    evidence_dir=root / "evidence",
                    account="candidate@example.com",
                    inbound_message_id="message-1",
                    inbound_subject="Question",
                    decision=decision,
                    executable="/opt/homebrew/bin/gog",
                )
                second = send_reply_once(
                    database=root / "outbox.sqlite3",
                    evidence_dir=root / "evidence",
                    account="candidate@example.com",
                    inbound_message_id="message-1",
                    inbound_subject="Question",
                    decision=decision,
                    executable="/opt/homebrew/bin/gog",
                )
            self.assertEqual(call.call_count, 1)
            argv = call.call_args.args[0]
            self.assertIn("--reply-to-message-id", argv)
            self.assertIn("message-1", argv)
            self.assertIn("--reply-all", argv)
            self.assertIn("--body-file", argv)
            self.assertNotIn(decision["body"], argv)
            body_path = Path(argv[argv.index("--body-file") + 1])
            self.assertEqual(body_path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(first["status"], "sent")
            self.assertEqual(second, first)

    def test_uncertain_send_is_never_blindly_retried(self):
        decision = build_approved_reply(
            self.profile,
            question_kind="location",
            question_source_span="Where are you based?",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            failed = type(
                "Completed",
                (),
                {"returncode": 1, "stdout": "", "stderr": "transport failed"},
            )()
            with patch("subprocess.run", return_value=failed) as call:
                with self.assertRaisesRegex(RuntimeError, "transport"):
                    send_reply_once(
                        database=root / "outbox.sqlite3",
                        evidence_dir=root / "evidence",
                        account="candidate@example.com",
                        inbound_message_id="message-2",
                        inbound_subject="Question",
                        decision=decision,
                    )
                with self.assertRaises(DeliveryUncertain):
                    send_reply_once(
                        database=root / "outbox.sqlite3",
                        evidence_dir=root / "evidence",
                        account="candidate@example.com",
                        inbound_message_id="message-2",
                        inbound_subject="Question",
                        decision=decision,
                    )
            self.assertEqual(call.call_count, 1)

    def test_self_round_trip_uses_explicit_recipient_but_keeps_threading(self):
        decision = build_approved_reply(
            self.profile,
            question_kind="location",
            question_source_span="Where are you based?",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            completed = type(
                "Completed",
                (),
                {
                    "returncode": 0,
                    "stdout": json.dumps(
                        {"messageId": "reply-self", "threadId": "thread-self"}
                    ),
                    "stderr": "",
                },
            )()
            with patch("subprocess.run", return_value=completed) as call:
                send_reply_once(
                    database=root / "outbox.sqlite3",
                    evidence_dir=root / "evidence",
                    account="candidate@example.com",
                    inbound_message_id="message-self",
                    inbound_subject="Question",
                    decision=decision,
                    allow_self_recipient=True,
                )
            argv = call.call_args.args[0]
            self.assertIn("--reply-to-message-id", argv)
            self.assertIn("--to", argv)
            self.assertIn("candidate@example.com", argv)
            self.assertNotIn("--reply-all", argv)


if __name__ == "__main__":
    unittest.main()
