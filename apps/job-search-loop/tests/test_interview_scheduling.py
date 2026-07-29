import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import call, patch

from job_search_loop.interview_scheduling import (
    SchedulingError,
    build_confirmation_reply,
    confirm_interview_slot,
    ensure_interview_event,
    find_interview_event,
    normalize_candidate_slots,
    query_busy_intervals,
    select_available_slot,
)
from job_search_loop.interview_prep import PrepStore


class InterviewSchedulingTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 7, 28, 0, 0, tzinfo=timezone.utc)
        self.raw_slots = [
            {
                "start": "2026-08-03T10:00:00+09:00",
                "end": "2026-08-03T11:00:00+09:00",
                "source_span": "August 3, 10:00–11:00 JST",
            },
            {
                "start": "2026-08-04T14:00:00+09:00",
                "end": "2026-08-04T15:00:00+09:00",
                "source_span": "August 4, 14:00–15:00 JST",
            },
        ]

    def test_candidate_slots_require_explicit_timezone_and_source_span(self):
        slots = normalize_candidate_slots(self.raw_slots, now=self.now)
        self.assertEqual(len(slots), 2)
        self.assertEqual(slots[0].source_span, "August 3, 10:00–11:00 JST")
        with self.assertRaisesRegex(SchedulingError, "timezone"):
            normalize_candidate_slots(
                [
                    {
                        "start": "2026-08-03T10:00:00",
                        "end": "2026-08-03T11:00:00",
                        "source_span": "August 3 at 10",
                    }
                ],
                now=self.now,
            )
        with self.assertRaisesRegex(SchedulingError, "source"):
            normalize_candidate_slots(
                [
                    {
                        "start": "2026-08-03T10:00:00+09:00",
                        "end": "2026-08-03T11:00:00+09:00",
                        "source_span": " ",
                    }
                ],
                now=self.now,
            )

    def test_inbox_prompt_executes_bounded_scheduling_workflow(self):
        root = Path(__file__).parents[1]
        prompt = (root / "prompts" / "inbox-pass.md").read_text(encoding="utf-8")
        self.assertIn("confirm_interview_slot", prompt)
        self.assertIn("timezone", prompt)
        self.assertIn("source_span", prompt)
        self.assertIn("earliest", prompt)

    def test_candidate_slots_reject_past_or_invalid_duration(self):
        for raw in (
            {
                "start": "2026-07-27T10:00:00+09:00",
                "end": "2026-07-27T11:00:00+09:00",
                "source_span": "July 27",
            },
            {
                "start": "2026-08-03T10:00:00+09:00",
                "end": "2026-08-03T10:05:00+09:00",
                "source_span": "August 3",
            },
        ):
            with self.subTest(raw=raw):
                with self.assertRaises(SchedulingError):
                    normalize_candidate_slots([raw], now=self.now)

    def test_earliest_non_conflicting_explicit_slot_is_selected(self):
        slots = normalize_candidate_slots(self.raw_slots, now=self.now)
        busy = [
            (
                datetime.fromisoformat("2026-08-03T00:30:00+00:00"),
                datetime.fromisoformat("2026-08-03T02:00:00+00:00"),
            )
        ]
        selected = select_available_slot(slots, busy)
        self.assertEqual(selected, slots[1])

    @patch("subprocess.run")
    def test_query_busy_uses_primary_calendar_and_full_candidate_range(self, run):
        run.return_value = type(
            "Completed",
            (),
            {
                "returncode": 0,
                "stdout": json.dumps(
                    {
                        "calendars": {
                            "primary": {
                                "busy": [
                                    {
                                        "start": "2026-08-03T01:00:00Z",
                                        "end": "2026-08-03T02:00:00Z",
                                    }
                                ]
                            }
                        }
                    }
                ),
                "stderr": "",
            },
        )()
        slots = normalize_candidate_slots(self.raw_slots, now=self.now)
        intervals = query_busy_intervals(
            account="candidate@example.com",
            slots=slots,
            executable="/opt/homebrew/bin/gog",
        )
        self.assertEqual(len(intervals), 1)
        argv = run.call_args.args[0]
        self.assertEqual(argv[:4], ["/opt/homebrew/bin/gog", "calendar", "freebusy", "primary"])
        self.assertIn("--from", argv)
        self.assertIn("--to", argv)

    @patch("subprocess.run")
    def test_existing_thread_event_is_updated_not_duplicated(self, run):
        run.side_effect = [
            type(
                "Completed",
                (),
                {
                    "returncode": 0,
                    "stdout": json.dumps(
                        [
                            {
                                "id": "existing-event",
                                "summary": "Old interview",
                                "start": {"dateTime": "2026-08-02T10:00:00+09:00"},
                                "end": {"dateTime": "2026-08-02T11:00:00+09:00"},
                            }
                        ]
                    ),
                    "stderr": "",
                },
            )(),
            type(
                "Completed",
                (),
                {
                    "returncode": 0,
                    "stdout": json.dumps({"id": "existing-event", "status": "confirmed"}),
                    "stderr": "",
                },
            )(),
        ]
        slot = normalize_candidate_slots(self.raw_slots, now=self.now)[0]
        result = ensure_interview_event(
            account="candidate@example.com",
            thread_id="thread-1",
            company="Example AI",
            role="AI Product Manager",
            slot=slot,
            executable="/opt/homebrew/bin/gog",
            now=self.now,
        )
        self.assertEqual(result["action"], "updated")
        commands = [item.args[0][2] for item in run.call_args_list]
        self.assertEqual(commands, ["events", "update"])
        self.assertNotIn("create", commands)

    @patch("subprocess.run")
    def test_missing_event_is_created_with_private_thread_key_and_reminders(self, run):
        run.side_effect = [
            type(
                "Completed",
                (),
                {"returncode": 0, "stdout": "[]", "stderr": ""},
            )(),
            type(
                "Completed",
                (),
                {
                    "returncode": 0,
                    "stdout": json.dumps({"id": "created-event", "status": "confirmed"}),
                    "stderr": "",
                },
            )(),
        ]
        slot = normalize_candidate_slots(self.raw_slots, now=self.now)[0]
        result = ensure_interview_event(
            account="candidate@example.com",
            thread_id="thread-1",
            company="Example AI",
            role="AI Product Manager",
            slot=slot,
            executable="/opt/homebrew/bin/gog",
            now=self.now,
        )
        self.assertEqual(result["action"], "created")
        create_argv = run.call_args_list[1].args[0]
        self.assertEqual(create_argv[2], "create")
        self.assertEqual(create_argv.count("--reminder"), 2)
        private_values = [
            create_argv[index + 1]
            for index, value in enumerate(create_argv)
            if value == "--private-prop"
        ]
        self.assertTrue(any(value.startswith("anicca_job_thread=") for value in private_values))
        self.assertTrue(any(value.startswith("anicca_job_event=") for value in private_values))

    def test_confirmation_reply_contains_only_selected_explicit_time(self):
        slot = normalize_candidate_slots(self.raw_slots, now=self.now)[0]
        reply = build_confirmation_reply(slot)
        self.assertEqual(reply["action"], "auto_reply")
        self.assertIn("August 3", reply["body"])
        self.assertIn("10:00", reply["body"])
        self.assertNotIn("August 4", reply["body"])

    @patch("job_search_loop.interview_scheduling.send_reply_once")
    @patch("job_search_loop.interview_scheduling.ensure_interview_event")
    @patch("job_search_loop.interview_scheduling.find_interview_event")
    @patch("job_search_loop.interview_scheduling.query_busy_intervals")
    def test_confirmation_creates_calendar_before_threaded_reply(
        self,
        busy,
        find,
        ensure,
        send,
    ):
        order = []
        find.return_value = None
        busy.return_value = []
        ensure.side_effect = lambda **kwargs: (
            order.append("calendar")
            or {
                "action": "created",
                "event_id": "event-1",
                "event_key": "key-1",
            }
        )
        send.side_effect = lambda **kwargs: (
            order.append("reply")
            or {"status": "sent", "message_id": "reply-1"}
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = confirm_interview_slot(
                database=root / "outbox.sqlite3",
                prep_database=root / "prep.sqlite3",
                evidence_dir=root / "evidence",
                account="candidate@example.com",
                inbound_message_id="message-1",
                inbound_subject="Interview availability",
                thread_id="thread-1",
                company="Example AI",
                role="AI Product Manager",
                raw_slots=self.raw_slots,
                now=self.now,
            )
            self.assertEqual(result["status"], "confirmed")
            self.assertEqual(result["calendar_event_id"], "event-1")
            self.assertEqual(ensure.call_count, 1)
            self.assertEqual(send.call_count, 1)
            self.assertEqual(order, ["calendar", "reply"])
            prep = PrepStore(root / "prep.sqlite3")
            pending = prep.pending_generation()
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0]["company"], "Example AI")
            prep.close()

    @patch("job_search_loop.interview_scheduling.send_reply_once")
    @patch("job_search_loop.interview_scheduling.ensure_interview_event")
    @patch("job_search_loop.interview_scheduling.find_interview_event")
    @patch("job_search_loop.interview_scheduling.query_busy_intervals")
    def test_no_available_slot_fails_closed_without_side_effects(
        self,
        busy,
        find,
        ensure,
        send,
    ):
        find.return_value = None
        slots = normalize_candidate_slots(self.raw_slots, now=self.now)
        busy.return_value = [(slot.start, slot.end) for slot in slots]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = confirm_interview_slot(
                database=root / "outbox.sqlite3",
                prep_database=root / "prep.sqlite3",
                evidence_dir=root / "evidence",
                account="candidate@example.com",
                inbound_message_id="message-1",
                inbound_subject="Interview availability",
                thread_id="thread-1",
                company="Example AI",
                role="AI Product Manager",
                raw_slots=self.raw_slots,
                now=self.now,
            )
        self.assertEqual(result["status"], "no_available_slot")
        ensure.assert_not_called()
        send.assert_not_called()

    @patch("job_search_loop.interview_scheduling.send_reply_once")
    @patch("job_search_loop.interview_scheduling.ensure_interview_event")
    @patch("job_search_loop.interview_scheduling.find_interview_event")
    @patch("job_search_loop.interview_scheduling.query_busy_intervals")
    def test_retry_reuses_own_calendar_event_without_treating_it_as_a_conflict(
        self,
        busy,
        find,
        ensure,
        send,
    ):
        find.return_value = {
            "id": "existing-event",
            "summary": "Interview: Example AI — AI Product Manager",
            "start": {"dateTime": "2026-08-03T10:00:00+09:00"},
            "end": {"dateTime": "2026-08-03T11:00:00+09:00"},
        }
        ensure.return_value = {
            "action": "existing",
            "event_id": "existing-event",
            "event_key": "key-1",
        }
        send.return_value = {"status": "sent", "message_id": "reply-1"}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = confirm_interview_slot(
                database=root / "outbox.sqlite3",
                prep_database=root / "prep.sqlite3",
                evidence_dir=root / "evidence",
                account="candidate@example.com",
                inbound_message_id="message-1",
                inbound_subject="Interview availability",
                thread_id="thread-1",
                company="Example AI",
                role="AI Product Manager",
                raw_slots=self.raw_slots,
                now=self.now,
            )
        self.assertEqual(result["status"], "confirmed")
        busy.assert_not_called()
        self.assertEqual(
            ensure.call_args.kwargs["existing_event"]["id"],
            "existing-event",
        )


if __name__ == "__main__":
    unittest.main()
