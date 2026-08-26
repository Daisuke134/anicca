import json
import tempfile
import unittest
from pathlib import Path

from job_search_loop.mercor_work_store import WorkStateStore, WorkStoreError


class MercorWorkStoreTests(unittest.TestCase):
    def test_transition_is_persisted_and_duplicate_event_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "work-events.jsonl"
            store = WorkStateStore(path)
            first = store.transition(
                work_id="application-1",
                event_id="event-selected",
                next_state="selected",
                evidence_ref="gmail://message-1",
            )
            duplicate = store.transition(
                work_id="application-1",
                event_id="event-selected",
                next_state="selected",
                evidence_ref="gmail://message-1",
            )

            self.assertEqual(first, duplicate)
            self.assertEqual(store.current_state("application-1"), "selected")
            self.assertEqual(len(path.read_text(encoding="utf-8").splitlines()), 1)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_conflicting_duplicate_and_unsettled_revenue_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            store = WorkStateStore(Path(directory) / "work-events.jsonl")
            store.transition(
                work_id="application-1",
                event_id="event-selected",
                next_state="selected",
                evidence_ref="gmail://message-1",
            )
            with self.assertRaises(WorkStoreError):
                store.transition(
                    work_id="application-1",
                    event_id="event-selected",
                    next_state="contracted",
                    evidence_ref="gmail://message-2",
                )
            with self.assertRaises(WorkStoreError):
                store.transition(
                    work_id="application-1",
                    event_id="event-paid",
                    next_state="paid_settled",
                    evidence_ref="gmail://offer",
                    payment_id="offer-1",
                    settlement_status="pending",
                    amount_usd="125.00",
                )

    def test_event_rows_are_replayable_without_private_profile_data(self):
        with tempfile.TemporaryDirectory() as directory:
            store = WorkStateStore(Path(directory) / "work-events.jsonl")
            store.transition(
                work_id="application-1",
                event_id="event-selected",
                next_state="selected",
                evidence_ref="gmail://message-1",
            )
            rows = store.events("application-1")
            self.assertEqual(rows[0]["state"], "selected")
            self.assertNotIn("resume", json.dumps(rows).casefold())
            self.assertNotIn("password", json.dumps(rows).casefold())


if __name__ == "__main__":
    unittest.main()
