import hashlib
import inspect
import tempfile
import threading
import unittest
from pathlib import Path

from job_search_loop.ledger import FenceError, Ledger


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db = Path(self.tempdir.name) / "ledger.sqlite3"
        self.ledger = Ledger(self.db)
        self.resume = Path(self.tempdir.name) / "resume.pdf"
        self.resume.write_bytes(b"%PDF-1.4\nverified resume\n")
        self.resume_sha256 = hashlib.sha256(self.resume.read_bytes()).hexdigest()
        self.application_id = self.ledger.add_application(
            "Example", "AI Engineer", "https://jobs.example.com/42"
        )

    def tearDown(self):
        self.ledger.close()
        self.tempdir.cleanup()

    def _ready(self, application_id=None):
        target = application_id or self.application_id
        self.ledger.transition(target, "qualified")
        self.ledger.transition(target, "materials_ready")

    def _claim(self, ledger, application_id, japan_day, payload_hash):
        return ledger.claim_submission(
            application_id,
            japan_day,
            payload_hash,
            resume_path=self.resume,
            resume_sha256=self.resume_sha256,
        )

    def test_duplicate_job_returns_same_application(self):
        duplicate = self.ledger.add_application(
            " example ",
            "ai engineer",
            "https://jobs.example.com/42/?utm_campaign=test",
        )
        self.assertEqual(duplicate, self.application_id)

    def test_events_reconstruct_state_after_reopen(self):
        self._ready()
        self.ledger.close()
        self.ledger = Ledger(self.db)
        self.assertEqual(
            self.ledger.current_state(self.application_id), "materials_ready"
        )
        self.assertEqual(len(self.ledger.events(self.application_id)), 3)

    def test_daily_quota_counts_submitted_and_unknown(self):
        self._ready()
        first = self._claim(
            self.ledger, self.application_id, "2026-07-28", "hash-1"
        )
        self.ledger.complete_submission(first.intent_id, first.fence, "submitted")
        second_id = self.ledger.add_application(
            "Other", "GenAI Engineer", "https://jobs.example.com/43"
        )
        self._ready(second_id)
        second = self._claim(self.ledger, second_id, "2026-07-28", "hash-2")
        self.ledger.complete_submission(second.intent_id, second.fence, "submit_unknown")
        third_id = self.ledger.add_application(
            "Third", "AI Product Engineer", "https://jobs.example.com/44"
        )
        self._ready(third_id)
        self.assertIsNone(
            self._claim(self.ledger, third_id, "2026-07-28", "hash-3")
        )
        self.assertEqual(self.ledger.daily_slot_count("2026-07-28"), 2)

    def test_not_submitted_releases_observable_daily_slot(self):
        self._ready()
        intent = self._claim(
            self.ledger, self.application_id, "2026-07-28", "hash"
        )
        self.assertEqual(self.ledger.daily_slot_count("2026-07-28"), 1)
        self.ledger.complete_submission(
            intent.intent_id, intent.fence, "not_submitted"
        )
        self.assertEqual(self.ledger.daily_slot_count("2026-07-28"), 0)

    def test_stale_fence_cannot_complete(self):
        self._ready()
        intent = self._claim(
            self.ledger, self.application_id, "2026-07-28", "hash"
        )
        with self.assertRaises(FenceError):
            self.ledger.complete_submission(
                intent.intent_id, intent.fence + 1, "submitted"
            )

    def test_unknown_is_not_retried(self):
        self._ready()
        intent = self._claim(
            self.ledger, self.application_id, "2026-07-28", "hash"
        )
        self.ledger.complete_submission(
            intent.intent_id, intent.fence, "submit_unknown"
        )
        self.assertIsNone(
            self._claim(
                self.ledger, self.application_id, "2026-07-29", "new-hash"
            )
        )

    def test_concurrent_claims_never_exceed_two(self):
        ids = [self.application_id]
        for index in range(1, 5):
            ids.append(
                self.ledger.add_application(
                    f"Company {index}",
                    "AI Engineer",
                    f"https://jobs.example.com/{index + 100}",
                )
            )
        for application_id in ids:
            self._ready(application_id)
        self.ledger.close()
        results = []
        lock = threading.Lock()

        def claim(application_id):
            local = Ledger(self.db)
            try:
                result = self._claim(
                    local,
                    application_id,
                    "2026-07-28",
                    f"hash-{application_id}",
                )
                with lock:
                    results.append(result)
            finally:
                local.close()

        threads = [threading.Thread(target=claim, args=(value,)) for value in ids]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.ledger = Ledger(self.db)
        self.assertEqual(sum(value is not None for value in results), 2)

    def test_submitted_application_retains_exact_resume_for_reporting(self):
        parameters = inspect.signature(self.ledger.claim_submission).parameters
        self.assertIn("resume_path", parameters)
        self.assertIn("resume_sha256", parameters)
        reports = getattr(self.ledger, "submitted_resume_reports", None)
        self.assertIsNotNone(reports)

        resume = Path(self.tempdir.name) / "Daisuke_AI_Resume.pdf"
        resume.write_bytes(b"%PDF-1.4\nverified resume\n")
        resume_sha256 = hashlib.sha256(resume.read_bytes()).hexdigest()
        self._ready()
        intent = self.ledger.claim_submission(
            self.application_id,
            "2026-07-29",
            "payload-hash",
            resume_path=resume,
            resume_sha256=resume_sha256,
        )
        self.ledger.complete_submission(intent.intent_id, intent.fence, "submitted")

        self.assertEqual(
            reports(),
            [
                {
                    "application_id": self.application_id,
                    "company": "Example",
                    "title": "AI Engineer",
                    "canonical_url": "https://jobs.example.com/42",
                    "resume_path": str(resume.resolve()),
                    "resume_sha256": resume_sha256,
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
