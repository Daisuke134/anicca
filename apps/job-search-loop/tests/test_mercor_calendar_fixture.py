import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from job_search_loop.calendar_sync import event_key
from job_search_loop.interview_scheduling import confirm_interview_slot


FIXTURE = Path(__file__).parent / "fixtures" / "mercor" / "interview-invitation.json"


class MercorCalendarFixtureTests(unittest.TestCase):
    def test_mercor_invitation_uses_freebusy_and_idempotent_calendar_key(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        now = datetime(2026, 8, 22, 0, 0, tzinfo=timezone.utc)
        order: list[str] = []
        with (
            patch("job_search_loop.interview_scheduling.find_interview_event", return_value=None),
            patch(
                "job_search_loop.interview_scheduling.query_busy_intervals",
                return_value=[],
            ) as busy,
            patch(
                "job_search_loop.interview_scheduling.ensure_interview_event",
                side_effect=lambda **kwargs: (
                    order.append("calendar")
                    or {
                        "action": "created",
                        "event_id": "mercor-event-synthetic-001",
                        "event_key": event_key(payload["thread_id"], kwargs["slot"].start),
                    }
                ),
            ) as ensure,
            patch(
                "job_search_loop.interview_scheduling.send_reply_once",
                side_effect=lambda **kwargs: (
                    order.append("reply")
                    or {"status": "sent", "message_id": "mercor-reply-synthetic-001"}
                ),
            ) as reply,
        ):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                result = confirm_interview_slot(
                    database=root / "outbox.sqlite3",
                    prep_database=root / "prep.sqlite3",
                    evidence_dir=root / "evidence",
                    account="operator@example.invalid",
                    inbound_message_id=payload["message_id"],
                    inbound_subject=payload["subject"],
                    thread_id=payload["thread_id"],
                    company=payload["company"],
                    role=payload["role"],
                    candidate_name="Mercor Candidate",
                    raw_slots=payload["slots"],
                    now=now,
                )

        self.assertEqual(result["status"], "confirmed")
        self.assertEqual(result["calendar_action"], "created")
        self.assertEqual(order, ["calendar", "reply"])
        busy.assert_called_once()
        ensure.assert_called_once()
        reply.assert_called_once()
        self.assertEqual(
            result["calendar_event_key"],
            event_key(payload["thread_id"], datetime.fromisoformat(payload["slots"][0]["start"])),
        )


if __name__ == "__main__":
    unittest.main()
