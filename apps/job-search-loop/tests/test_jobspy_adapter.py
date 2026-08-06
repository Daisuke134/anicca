import tempfile
import unittest
from pathlib import Path

from job_search_loop.candidate_queue import CandidateQueue
from job_search_loop.jobspy_adapter import ingest_jobspy_rows


class JobSpyAdapterTests(unittest.TestCase):
    def test_direct_official_application_url_is_preferred_and_provenance_is_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = CandidateQueue(Path(directory) / "candidates.sqlite3")
            try:
                receipt = ingest_jobspy_rows(
                    queue,
                    [
                        {
                            "title": "Solutions Architect",
                            "company": "Acme",
                            "site": "linkedin",
                            "job_url": "https://linkedin.example/jobs/123",
                            "job_url_direct": "https://jobs.acme.example/roles/123?utm_source=linkedin",
                        }
                    ],
                    query_family="six_figure_japan",
                )
                pending = queue.pending(limit=10)
            finally:
                queue.close()

        self.assertEqual(receipt["inserted_count"], 1)
        self.assertEqual(receipt["rejected_row_count"], 0)
        self.assertEqual(
            pending,
            [{
                "url": "https://jobs.acme.example/roles/123",
                "source": "jobspy:linkedin:official_direct",
                "query_family": "six_figure_japan",
            }],
        )

    def test_tracking_variants_are_canonically_deduped_by_existing_queue(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = CandidateQueue(Path(directory) / "candidates.sqlite3")
            try:
                receipt = ingest_jobspy_rows(
                    queue,
                    [
                        {"title": "AI Engineer", "company": "Acme", "site": "indeed", "job_url": "https://jobs.example/roles/7?utm_source=indeed"},
                        {"title": "AI Engineer", "company": "Acme", "site": "glassdoor", "job_url": "https://jobs.example/roles/7?utm_source=glassdoor"},
                    ],
                    query_family="strong_fit",
                )
            finally:
                queue.close()

        self.assertEqual(receipt["observed_count"], 2)
        self.assertEqual(receipt["inserted_count"], 1)
        self.assertEqual(receipt["duplicate_count"], 1)

    def test_malformed_rows_are_rejected_before_queue_ingestion(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = CandidateQueue(Path(directory) / "candidates.sqlite3")
            try:
                receipt = ingest_jobspy_rows(
                    queue,
                    [None, {}, {"title": "Missing company", "job_url": "javascript:alert(1)"}],
                    query_family="dream",
                )
                summary = queue.summary()
            finally:
                queue.close()

        self.assertEqual(receipt["rejected_row_count"], 3)
        self.assertEqual(receipt["inserted_count"], 0)
        self.assertEqual(summary["discovered_count"], 0)


if __name__ == "__main__":
    unittest.main()
