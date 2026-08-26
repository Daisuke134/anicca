import json
import tempfile
import unittest
from pathlib import Path

from job_search_loop.mercor_bank_sync import sync_bank_snapshot
from job_search_loop.mercor_work_store import WorkStateStore, WorkStoreError


class MercorBankSyncTests(unittest.TestCase):
    def _paid_store(self, path: Path) -> WorkStateStore:
        store = WorkStateStore(path)
        for state in ("selected", "contracted", "authorized_work", "work_submitted", "accepted"):
            extra = {"authorization_policy": "explicitly_allowed"} if state == "authorized_work" else {}
            if state == "accepted":
                extra = {"acceptance_status": "accepted"}
            store.transition(
                work_id="application-1",
                event_id=f"event-{state}",
                next_state=state,
                evidence_ref=f"evidence://{state}",
                **extra,
            )
        store.transition(
            work_id="application-1",
            event_id="payment-pay-1",
            next_state="paid_settled",
            evidence_ref="mercor://payment/pay-1",
            payment_id="pay-1",
            settlement_status="paid",
            amount_usd="125.00",
        )
        return store

    def _snapshot(self, path: Path, *, payment_id: str = "pay-1") -> None:
        path.write_text(
            json.dumps(
                {
                    "provider": "mercor",
                    "observed_at": "2026-08-26T08:00:00Z",
                    "rows": [
                        {
                            "work_id": "application-1",
                            "payment_id": payment_id,
                            "payout_id": "payout-1",
                            "bank_transaction_id": "bank-1",
                            "status": "matched",
                            "amount_usd": "125.00",
                            "evidence_ref": "bank://transaction/bank-1",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    def test_persists_bank_match_before_revenue(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store_path = root / "work-events.jsonl"
            self._paid_store(store_path)
            snapshot = root / "bank.json"
            self._snapshot(snapshot)

            result = sync_bank_snapshot(snapshot_path=snapshot, store_path=store_path)
            events = WorkStateStore(store_path).events("application-1")

        self.assertEqual(result, {"status": "matched", "synced_count": 1})
        self.assertEqual([row["state"] for row in events[-2:]], ["bank_matched", "revenue_recorded"])
        self.assertEqual(events[-2]["bank_transaction_id"], "bank-1")

    def test_rejects_bank_match_for_another_payment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store_path = root / "work-events.jsonl"
            self._paid_store(store_path)
            snapshot = root / "bank.json"
            self._snapshot(snapshot, payment_id="pay-other")

            with self.assertRaisesRegex(WorkStoreError, "payment_id"):
                sync_bank_snapshot(snapshot_path=snapshot, store_path=store_path)
            self.assertEqual(WorkStateStore(store_path).current_state("application-1"), "paid_settled")


if __name__ == "__main__":
    unittest.main()
