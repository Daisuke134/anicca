import tempfile
import unittest
import json
from pathlib import Path

from job_search_loop.candidate_queue import CandidateQueue, TerminalResultError


class CandidateQueueTests(unittest.TestCase):
    def test_browser_result_contract_requires_discovery_verification_counts(self):
        schema = json.loads(
            (
                Path(__file__).resolve().parents[1]
                / "schemas"
                / "pass-result.v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        self.assertTrue(
            {
                "discovered_link_count",
                "verified_link_count",
                "remaining_unverified_count",
            }.issubset(schema["required"])
        )

    def test_unverified_links_reject_clean_no_eligible_terminal_result(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = CandidateQueue(Path(directory) / "candidate-queue.sqlite3")
            try:
                queue.discover(
                    [
                        {
                            "url": f"https://jobs.example/roles/{index}",
                            "source": "official_browser",
                            "query_family": "strong_fit",
                        }
                        for index in range(102)
                    ]
                )

                with self.assertRaisesRegex(
                    TerminalResultError, "102 unverified candidate links remain"
                ):
                    queue.validate_terminal(
                        {
                            "status": "no_eligible_job_found",
                            "discovered_link_count": 102,
                            "verified_link_count": 0,
                            "remaining_unverified_count": 102,
                        }
                    )
            finally:
                queue.close()

    def test_terminal_no_eligible_is_allowed_only_after_queue_is_exhausted(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = CandidateQueue(Path(directory) / "candidate-queue.sqlite3")
            try:
                queue.discover(
                    [
                        {
                            "url": "https://jobs.example/roles/one",
                            "source": "official_browser",
                            "query_family": "dream",
                        }
                    ]
                )
                queue.mark_verified(
                    "https://jobs.example/roles/one",
                    eligible=False,
                    reason="posting_expired",
                )

                receipt = queue.validate_terminal(
                    {
                        "status": "no_eligible_job_found",
                        "discovered_link_count": 1,
                        "verified_link_count": 1,
                        "remaining_unverified_count": 0,
                    }
                )
            finally:
                queue.close()

        self.assertEqual(receipt["status"], "exhausted")
        self.assertEqual(receipt["remaining_unverified_count"], 0)

    def test_discovery_is_canonical_and_idempotent_across_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = CandidateQueue(Path(directory) / "candidate-queue.sqlite3")
            try:
                first = queue.discover(
                    [
                        {
                            "url": "https://jobs.example/roles/one?utm_source=first",
                            "source": "google",
                            "query_family": "dream",
                        }
                    ]
                )
                second = queue.discover(
                    [
                        {
                            "url": "https://jobs.example/roles/one?utm_source=second",
                            "source": "official_browser",
                            "query_family": "dream",
                        }
                    ]
                )
                summary = queue.summary()
                pending = queue.pending(limit=10)
            finally:
                queue.close()

        self.assertEqual(first["inserted_count"], 1)
        self.assertEqual(second["inserted_count"], 0)
        self.assertEqual(summary["discovered_count"], 1)
        self.assertEqual(summary["remaining_unverified_count"], 1)
        self.assertEqual(
            pending,
            [
                {
                    "url": "https://jobs.example/roles/one",
                    "source": "google",
                    "query_family": "dream",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
