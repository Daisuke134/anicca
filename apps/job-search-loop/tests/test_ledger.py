import hashlib
import inspect
import json
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
        row = ledger.connection.execute(
            "SELECT canonical_url FROM applications WHERE id = ?",
            (application_id,),
        ).fetchone()
        snapshot = Path(self.tempdir.name) / f"ats-{application_id}.json"
        snapshot.write_text(
            json.dumps(
                {
                    "version": 1,
                    "url": str(row["canonical_url"]),
                    "navigation_committed": True,
                    "frames": [
                        {
                            "url": str(row["canonical_url"]),
                            "controls": [
                                {
                                    "tag": "input",
                                    "type": "email",
                                    "role": None,
                                    "label": "Email",
                                    "name": "email",
                                    "text": "",
                                },
                                {
                                    "tag": "input",
                                    "type": "file",
                                    "role": None,
                                    "label": "Resume",
                                    "name": "resume",
                                    "text": "",
                                },
                                {
                                    "tag": "button",
                                    "type": "submit",
                                    "role": "button",
                                    "label": None,
                                    "name": "submit",
                                    "text": "Submit Application",
                                },
                            ],
                        }
                    ],
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        snapshot_sha256 = hashlib.sha256(snapshot.read_bytes()).hexdigest()
        return ledger.claim_submission(
            application_id,
            japan_day,
            payload_hash,
            resume_path=self.resume,
            resume_sha256=self.resume_sha256,
            ats_snapshot_path=snapshot,
            ats_snapshot_sha256=snapshot_sha256,
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

    def test_not_submitted_reopens_with_new_fence_and_attempt_history(self):
        self._ready()
        first = self._claim(
            self.ledger, self.application_id, "2026-07-28", "hash-before"
        )
        self.ledger.complete_submission(
            first.intent_id, first.fence, "not_submitted"
        )

        retryable = self.ledger.retryable_applications()
        self.assertEqual(
            retryable,
            [
                {
                    "application_id": self.application_id,
                    "company": "Example",
                    "title": "AI Engineer",
                    "canonical_url": "https://jobs.example.com/42",
                    "intent_id": first.intent_id,
                    "fence": 1,
                }
            ],
        )

        second = self._claim(
            self.ledger, self.application_id, "2026-07-29", "hash-after"
        )
        self.assertIsNotNone(second)
        self.assertEqual(second.intent_id, first.intent_id)
        self.assertEqual(second.fence, first.fence + 1)
        self.assertEqual(self.ledger.current_state(self.application_id), "submit_claimed")
        self.assertEqual(self.ledger.daily_slot_count("2026-07-29"), 1)
        self.assertEqual(self.ledger.retryable_applications(), [])

        with self.assertRaises(FenceError):
            self.ledger.complete_submission(
                first.intent_id, first.fence, "submitted"
            )

        attempts = self.ledger.submission_attempts(self.application_id)
        self.assertEqual(
            [(row["fence"], row["payload_hash"], row["status"]) for row in attempts],
            [
                (1, "hash-before", "not_submitted"),
                (2, "hash-after", "submit_claimed"),
            ],
        )

        self.ledger.complete_submission(
            second.intent_id, second.fence, "submitted"
        )
        self.assertEqual(
            [(row["fence"], row["status"]) for row in self.ledger.submission_attempts(self.application_id)],
            [(1, "not_submitted"), (2, "submitted")],
        )

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

    def test_submitted_is_not_retried(self):
        self._ready()
        intent = self._claim(
            self.ledger, self.application_id, "2026-07-28", "hash"
        )
        self.ledger.complete_submission(intent.intent_id, intent.fence, "submitted")
        self.assertIsNone(
            self._claim(
                self.ledger, self.application_id, "2026-07-29", "new-hash"
            )
        )
        self.assertEqual(self.ledger.retryable_applications(), [])

    def test_existing_intent_is_backfilled_into_attempt_history(self):
        self._ready()
        intent = self._claim(
            self.ledger, self.application_id, "2026-07-28", "legacy-hash"
        )
        self.ledger.complete_submission(
            intent.intent_id, intent.fence, "not_submitted"
        )
        self.ledger.connection.execute("DROP TABLE submission_attempts")
        self.ledger.close()

        self.ledger = Ledger(self.db)
        attempts = self.ledger.submission_attempts(self.application_id)
        self.assertEqual(
            [(row["fence"], row["payload_hash"], row["status"]) for row in attempts],
            [(1, "legacy-hash", "not_submitted")],
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

    def test_snapshot_hash_mismatch_cannot_claim_or_consume_slot(self):
        self._ready()
        with self.assertRaisesRegex(ValueError, "ATS snapshot SHA-256"):
            self.ledger.claim_submission(
                self.application_id,
                "2026-07-29",
                "payload",
                resume_path=self.resume,
                resume_sha256=self.resume_sha256,
                ats_snapshot_path=Path(self.tempdir.name) / "missing.json",
                ats_snapshot_sha256="0" * 64,
            )
        self.assertEqual(self.ledger.daily_slot_count("2026-07-29"), 0)

    def test_non_ready_snapshot_cannot_claim_or_consume_slot(self):
        self._ready()
        snapshot = Path(self.tempdir.name) / "not-ready.json"
        snapshot.write_text(
            json.dumps(
                {
                    "version": 1,
                    "url": "https://jobs.example.com/42",
                    "navigation_committed": True,
                    "frames": [
                        {
                            "url": "https://jobs.example.com/42",
                            "controls": [],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "ATS snapshot is not ready"):
            self.ledger.claim_submission(
                self.application_id,
                "2026-07-29",
                "payload",
                resume_path=self.resume,
                resume_sha256=self.resume_sha256,
                ats_snapshot_path=snapshot,
                ats_snapshot_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest(),
            )
        self.assertEqual(self.ledger.daily_slot_count("2026-07-29"), 0)

    def test_snapshot_for_another_job_cannot_claim_or_consume_slot(self):
        self._ready()
        snapshot = Path(self.tempdir.name) / "wrong-job.json"
        snapshot.write_text(
            json.dumps(
                {
                    "version": 1,
                    "url": "https://jobs.example.com/another-job",
                    "navigation_committed": True,
                    "frames": [
                        {
                            "url": "https://jobs.example.com/another-job",
                            "controls": [
                                {"tag": "input", "type": "email"},
                                {"tag": "input", "type": "file"},
                                {
                                    "tag": "button",
                                    "type": "submit",
                                    "text": "Submit Application",
                                },
                            ],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "ATS snapshot URL"):
            self.ledger.claim_submission(
                self.application_id,
                "2026-07-29",
                "payload",
                resume_path=self.resume,
                resume_sha256=self.resume_sha256,
                ats_snapshot_path=snapshot,
                ats_snapshot_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest(),
            )
        self.assertEqual(self.ledger.daily_slot_count("2026-07-29"), 0)

    def test_workday_job_surface_is_ready_for_navigation_but_not_for_claim(self):
        fixture = (
            Path(__file__).parent
            / "fixtures"
            / "ats"
            / "workday-job-surface.json"
        )
        snapshot = json.loads(fixture.read_text(encoding="utf-8"))
        application_id = self.ledger.add_application(
            "Example Workday",
            "AI Sales Engineer",
            snapshot["url"],
        )
        self._ready(application_id)
        with self.assertRaisesRegex(ValueError, "ATS snapshot is not claim-ready"):
            self.ledger.claim_submission(
                application_id,
                "2026-07-29",
                "payload",
                resume_path=self.resume,
                resume_sha256=self.resume_sha256,
                ats_snapshot_path=fixture,
                ats_snapshot_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
            )
        self.assertEqual(self.ledger.daily_slot_count("2026-07-29"), 0)

    def test_workday_apply_choice_is_ready_for_navigation_but_not_for_claim(self):
        fixture = (
            Path(__file__).parent
            / "fixtures"
            / "ats"
            / "workday-apply-choice-surface.json"
        )
        snapshot = json.loads(fixture.read_text(encoding="utf-8"))
        application_id = self.ledger.add_application(
            "Example Workday Choice",
            "AI Sales Engineer",
            snapshot["url"],
        )
        self._ready(application_id)
        with self.assertRaisesRegex(ValueError, "ATS snapshot is not claim-ready"):
            self.ledger.claim_submission(
                application_id,
                "2026-07-29",
                "payload",
                resume_path=self.resume,
                resume_sha256=self.resume_sha256,
                ats_snapshot_path=fixture,
                ats_snapshot_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
            )
        self.assertEqual(self.ledger.daily_slot_count("2026-07-29"), 0)

    def test_workday_account_gate_is_ready_for_navigation_but_not_for_claim(self):
        fixture = (
            Path(__file__).parent
            / "fixtures"
            / "ats"
            / "workday-create-account-surface.json"
        )
        snapshot = json.loads(fixture.read_text(encoding="utf-8"))
        application_id = self.ledger.add_application(
            "Example Workday Account",
            "AI Sales Engineer",
            snapshot["url"],
        )
        self._ready(application_id)
        with self.assertRaisesRegex(ValueError, "ATS snapshot is not claim-ready"):
            self.ledger.claim_submission(
                application_id,
                "2026-07-29",
                "payload",
                resume_path=self.resume,
                resume_sha256=self.resume_sha256,
                ats_snapshot_path=fixture,
                ats_snapshot_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
            )
        self.assertEqual(self.ledger.daily_slot_count("2026-07-29"), 0)

    def test_submitted_application_retains_exact_resume_for_reporting(self):
        parameters = inspect.signature(self.ledger.claim_submission).parameters
        self.assertIn("resume_path", parameters)
        self.assertIn("resume_sha256", parameters)
        self.assertIn("ats_snapshot_path", parameters)
        self.assertIn("ats_snapshot_sha256", parameters)
        reports = getattr(self.ledger, "submitted_resume_reports", None)
        self.assertIsNotNone(reports)

        resume = Path(self.tempdir.name) / "Daisuke_AI_Resume.pdf"
        resume.write_bytes(b"%PDF-1.4\nverified resume\n")
        resume_sha256 = hashlib.sha256(resume.read_bytes()).hexdigest()
        self._ready()
        ats_snapshot = Path(self.tempdir.name) / f"ats-{self.application_id}.json"
        ats_snapshot.write_text(
            json.dumps(
                {
                    "version": 1,
                    "url": "https://jobs.example.com/42",
                    "navigation_committed": True,
                    "frames": [
                        {
                            "url": "https://jobs.example.com/42",
                            "controls": [
                                {"tag": "input", "type": "email"},
                                {"tag": "input", "type": "file"},
                                {
                                    "tag": "button",
                                    "type": "submit",
                                    "text": "Submit Application",
                                },
                            ],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        ats_sha256 = hashlib.sha256(ats_snapshot.read_bytes()).hexdigest()
        intent = self.ledger.claim_submission(
            self.application_id,
            "2026-07-29",
            "payload-hash",
            resume_path=resume,
            resume_sha256=resume_sha256,
            ats_snapshot_path=ats_snapshot,
            ats_snapshot_sha256=ats_sha256,
        )
        self.assertEqual(intent.ats_snapshot_path, str(ats_snapshot.resolve()))
        self.assertEqual(intent.ats_snapshot_sha256, ats_sha256)
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
