import tempfile
import unittest
import json
from pathlib import Path

from job_search_loop.candidate_queue import CandidateQueue, TerminalResultError


class CandidateQueueTests(unittest.TestCase):
    def test_prefilter_shortlist_becomes_immediately_actionable(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = CandidateQueue(Path(directory) / "candidate-queue.sqlite3")
            try:
                queue.ingest_prefilter(
                    [
                        {
                            "official_url": "https://jobs.example/roles/agentic-ai",
                            "provider": "workday_cxs",
                            "bucket": "dream",
                            "company": "Example",
                            "title": "Solution Architect - Agentic AI",
                            "gate_status": "pass",
                            "ranking_ready": True,
                        },
                        {
                            "official_url": "https://jobs.example/roles/review",
                            "provider": "official_ats_boards",
                            "bucket": "strong_fit",
                            "company": "Example Two",
                            "title": "AI Product Lead",
                            "gate_status": "needs_verification",
                            "ranking_ready": True,
                        },
                    ]
                )
                summary = queue.summary()
            finally:
                queue.close()

        self.assertEqual(summary["eligible_count"], 1)
        self.assertEqual(summary["remaining_unverified_count"], 1)

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

    def test_company_role_repost_is_deduped_across_urls_and_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = CandidateQueue(Path(directory) / "candidate-queue.sqlite3")
            try:
                first = queue.discover(
                    [
                        {
                            "url": "https://jobs.example/roles/old",
                            "source": "official",
                            "query_family": "dream",
                            "company": "Acme, Inc.",
                            "title": "AI Deployment Engineer (Tokyo)",
                        }
                    ]
                )
                second = queue.discover(
                    [
                        {
                            "url": "https://jobs.example/roles/new",
                            "source": "official",
                            "query_family": "dream",
                            "company": "Acme Inc",
                            "title": "AI Deployment Engineer [Remote]",
                        }
                    ]
                )
            finally:
                queue.close()

        self.assertEqual(first["inserted_count"], 1)
        self.assertEqual(second["inserted_count"], 0)
        self.assertEqual(second["duplicate_count"], 1)

    def test_rejected_role_does_not_hide_a_new_live_requisition(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = CandidateQueue(Path(directory) / "candidate-queue.sqlite3")
            try:
                queue.discover(
                    [
                        {
                            "url": "https://jobs.example/roles/expired",
                            "source": "official",
                            "query_family": "dream",
                            "company": "Acme",
                            "title": "AI Engineer",
                        }
                    ]
                )
                queue.mark_verified(
                    "https://jobs.example/roles/expired",
                    eligible=False,
                    reason="posting_expired",
                )
                next_role = queue.discover(
                    [
                        {
                            "url": "https://jobs.example/roles/live",
                            "source": "official",
                            "query_family": "dream",
                            "company": "Acme",
                            "title": "AI Engineer",
                        }
                    ]
                )
            finally:
                queue.close()

        self.assertEqual(next_role["inserted_count"], 1)

    def test_cross_company_near_verbatim_jd_is_deduped_by_fingerprint(self):
        from job_search_loop.dedup import fingerprint_text

        body = " ".join(["Build reliable AI systems for enterprise customers"] * 14)
        fingerprint = fingerprint_text(body)
        with tempfile.TemporaryDirectory() as directory:
            queue = CandidateQueue(Path(directory) / "candidate-queue.sqlite3")
            try:
                result = queue.discover(
                    [
                        {
                            "url": "https://company.example/role",
                            "source": "official",
                            "query_family": "dream",
                            "company": "Company",
                            "title": "AI Engineer",
                            "jd_fingerprint": fingerprint,
                        },
                        {
                            "url": "https://agency.example/role",
                            "source": "official",
                            "query_family": "dream",
                            "company": "Agency",
                            "title": "Machine Learning Consultant",
                            "jd_fingerprint": fingerprint,
                        },
                    ]
                )
            finally:
                queue.close()

        self.assertEqual(result["inserted_count"], 1)
        self.assertEqual(result["duplicate_count"], 1)


if __name__ == "__main__":
    unittest.main()
