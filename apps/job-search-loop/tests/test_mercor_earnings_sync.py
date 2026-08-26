import json
import tempfile
import unittest
from pathlib import Path

from job_search_loop.mercor_earnings_sync import sync_earnings_snapshot
from job_search_loop.mercor_work_store import WorkStateStore


class MercorEarningsSyncTests(unittest.TestCase):
    def test_unacknowledged_payout_report_is_delivery_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._store_accepted(root / "work-events.jsonl")
            snapshot = root / "earnings.json"
            snapshot.write_text(
                json.dumps(
                    {
                        "provider": "mercor",
                        "page_url": "https://work.mercor.com/earnings",
                        "observed_at": "2026-08-22T12:00:00+00:00",
                        "total_earnings_usd": "125.00",
                        "payment_history_status": "has_rows",
                        "rows": [{"payment_id": "pay-unacknowledged", "status": "Paid", "earned_usd": "125.00", "payout_date": "2026-08-22", "work_id": "application-1"}],
                    }
                ),
                encoding="utf-8",
            )
            result = sync_earnings_snapshot(
                snapshot_path=snapshot,
                store_path=root / "work-events.jsonl",
                outbox_path=root / "telegram.sqlite3",
                sender=lambda **_: {"status": "send_started", "message_id": None},
            )

        self.assertEqual(result["events"][0]["delivery"], "delivery_unknown")

    def _store_accepted(self, path: Path) -> WorkStateStore:
        store = WorkStateStore(path)
        for state in ("selected", "contracted", "authorized_work", "work_submitted", "accepted"):
            kwargs = {}
            if state == "authorized_work":
                kwargs["authorization_policy"] = "explicitly_allowed"
            if state == "accepted":
                kwargs["acceptance_status"] = "accepted"
            store.transition(
                work_id="application-1",
                event_id=f"event-{state}",
                next_state=state,
                evidence_ref=f"evidence://{state}",
                **kwargs,
            )
        return store

    def test_settled_row_advances_work_and_revenue(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = self._store_accepted(root / "work-events.jsonl")
            store.close = lambda: None
            snapshot = root / "earnings.json"
            snapshot.write_text(
                json.dumps(
                    {
                        "provider": "mercor",
                        "page_url": "https://work.mercor.com/earnings",
                        "observed_at": "2026-08-22T12:00:00+00:00",
                        "total_earnings_usd": "125.00",
                        "payment_history_status": "has_rows",
                        "rows": [
                            {
                                "payment_id": "pay-1",
                                "status": "Paid",
                                "earned_usd": "125.00",
                                "payout_date": "2026-08-22",
                                "work_id": "application-1",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            result = sync_earnings_snapshot(
                snapshot_path=snapshot,
                store_path=root / "work-events.jsonl",
                outbox_path=root / "telegram.sqlite3",
                sender=lambda **_: {"status": "sent", "message_id": "telegram-1"},
            )
            self.assertEqual(result["status"], "settled")
            self.assertEqual(result["synced_count"], 1)
            self.assertEqual(WorkStateStore(root / "work-events.jsonl").current_state("application-1"), "revenue_recorded")

    def test_no_payment_history_does_not_change_work_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._store_accepted(root / "work-events.jsonl")
            snapshot = root / "earnings.json"
            snapshot.write_text(
                json.dumps(
                    {
                        "provider": "mercor",
                        "page_url": "https://work.mercor.com/earnings",
                        "observed_at": "2026-08-22T12:00:00+00:00",
                        "total_earnings_usd": "0.00",
                        "payment_history_status": "empty",
                        "rows": [],
                    }
                ),
                encoding="utf-8",
            )
            result = sync_earnings_snapshot(
                snapshot_path=snapshot,
                store_path=root / "work-events.jsonl",
                outbox_path=root / "telegram.sqlite3",
                sender=lambda **_: (_ for _ in ()).throw(RuntimeError("must not send")),
            )
            self.assertEqual(result, {"status": "not_observed", "synced_count": 0, "events": []})
            self.assertEqual(WorkStateStore(root / "work-events.jsonl").current_state("application-1"), "accepted")


if __name__ == "__main__":
    unittest.main()
