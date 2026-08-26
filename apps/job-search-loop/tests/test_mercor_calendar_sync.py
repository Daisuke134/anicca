import tempfile
import unittest
from pathlib import Path

from job_search_loop.mercor_calendar_sync import sync_calendar_events
from job_search_loop.mercor_work_store import WorkStateStore


class MercorCalendarSyncTests(unittest.TestCase):
    def test_unacknowledged_calendar_report_is_delivery_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = sync_calendar_events(
                payload={
                    "mercor_calendar_events": [
                        {
                            "work_id": "application-1",
                            "event_id": "calendar-unacknowledged",
                            "calendar_event_key": "mercor:thread-1:2026-08-25T01:00:00+00:00",
                            "evidence_ref": "gmail://message-1",
                        }
                    ]
                },
                store_path=root / "work-events.jsonl",
                outbox_path=root / "telegram.sqlite3",
                sender=lambda **_: {"status": "send_started", "message_id": None},
            )

        self.assertEqual(result["events"][0]["delivery"], "delivery_unknown")

    def test_calendar_artifact_is_idempotent_and_does_not_authorize_work(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = {
                "mercor_calendar_events": [
                    {
                        "work_id": "application-1",
                        "event_id": "calendar-1",
                        "calendar_event_key": "mercor:thread-1:2026-08-25T01:00:00+00:00",
                        "evidence_ref": "gmail://message-1",
                    }
                ]
            }
            first = sync_calendar_events(
                payload=payload,
                store_path=root / "work-events.jsonl",
                outbox_path=root / "telegram.sqlite3",
                sender=lambda **_: {"status": "sent", "message_id": "telegram-1"},
            )
            second = sync_calendar_events(
                payload=payload,
                store_path=root / "work-events.jsonl",
                outbox_path=root / "telegram.sqlite3",
                sender=lambda **_: {"status": "sent", "message_id": "telegram-2"},
            )
            store = WorkStateStore(root / "work-events.jsonl")
            self.assertEqual(first["synced_count"], 1)
            self.assertEqual(second["synced_count"], 1)
            self.assertEqual(store.current_state("application-1"), "submitted_pending_review")
            self.assertEqual(store.artifacts("application-1")[0]["artifact_type"], "calendar_scheduled")


if __name__ == "__main__":
    unittest.main()
