import json
import os
import tempfile
import unittest
from pathlib import Path

from job_search_loop.browser_worker import (
    BrowserWorkerBusy,
    exclusive_worker,
    run_worker,
)
from job_search_loop.candidate_queue import CandidateQueue


class BrowserWorkerTests(unittest.TestCase):
    def test_exclusive_worker_rejects_a_second_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / "browser-worker.lock"
            with exclusive_worker(lock):
                with self.assertRaisesRegex(BrowserWorkerBusy, "already running"):
                    with exclusive_worker(lock):
                        self.fail("second worker acquired the same lock")

    def test_run_worker_writes_truthful_pending_receipts_without_submission(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "candidate-queue.sqlite3"
            queue = CandidateQueue(database)
            try:
                queue.discover(
                    [
                        {
                            "url": "https://jobs.ashbyhq.com/example/role-1",
                            "source": "official_ats_boards",
                            "query_family": "dream",
                        }
                    ]
                )
            finally:
                queue.close()
            owner_receipt = root / "browser-owner.json"
            owner_receipt.write_text(
                json.dumps(
                    {
                        "status": "ready",
                        "holder_pid": os.getpid(),
                        "lease_id": "lease-1",
                        "fence": 7,
                    }
                ),
                encoding="utf-8",
            )
            output = root / "result.json"
            receipt = root / "worker-receipt.json"

            result = run_worker(
                database=database,
                owner_receipt=owner_receipt,
                holder_pid=os.getpid(),
                run_id="daily-test",
                lock_path=root / "worker.lock",
                worker_receipt=receipt,
                output=output,
            )

            self.assertEqual(result["submitted"], [])
            self.assertEqual(result["submit_unknown"], [])
            self.assertEqual(result["remaining_unverified_count"], 1)
            self.assertEqual(
                result["blocked"], ["1_candidate_links_await_fill_adapter"]
            )
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
            recorded = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(recorded["status"], "completed")
            self.assertEqual(recorded["fence"], 7)
            self.assertEqual(recorded["submitted_count"], 0)

    def test_run_worker_rejects_a_mismatched_daily_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            owner_receipt = root / "browser-owner.json"
            owner_receipt.write_text(
                json.dumps({"status": "ready", "holder_pid": 999999}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RuntimeError, "does not match"):
                run_worker(
                    database=root / "candidate-queue.sqlite3",
                    owner_receipt=owner_receipt,
                    holder_pid=os.getpid(),
                    run_id="daily-test",
                    lock_path=root / "worker.lock",
                    worker_receipt=root / "receipt.json",
                    output=root / "result.json",
                )


if __name__ == "__main__":
    unittest.main()
