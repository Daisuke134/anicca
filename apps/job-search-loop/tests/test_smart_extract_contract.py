import unittest
import tempfile
import json
from pathlib import Path

from job_search_loop.candidate_queue import CandidateQueue
from job_search_loop.smart_extract_contract import (
    ingest_site_pattern_captures,
    normalize_smart_extract_rows,
)


class SmartExtractContractTests(unittest.TestCase):
    def test_normalizes_json_ld_and_relative_official_urls_with_bounds(self):
        result = normalize_smart_extract_rows(
            [
                {
                    "@type": "JobPosting",
                    "title": "AI Solutions Architect",
                    "url": "/careers/ai-architect?utm_source=jobs",
                    "description": "x" * 5_000,
                    "jobLocation": {"address": {"addressLocality": "Tokyo", "addressCountry": "JP"}},
                }
            ],
            source_url="https://company.example/careers",
            strategy="json_ld",
            max_rows=10,
        )

        self.assertEqual(result["accepted_count"], 1)
        row = result["results"][0]
        self.assertEqual(row["url"], "https://company.example/careers/ai-architect")
        self.assertEqual(row["location"], "Tokyo, JP")
        self.assertEqual(len(row["description"]), 1_000)
        self.assertEqual(row["source_kind"], "official")
        self.assertEqual(row["discovery_provider"], "smart_extract:json_ld")

    def test_api_rows_are_capped_and_malformed_or_executable_plans_are_rejected(self):
        rows = [
            {"title": f"Engineer {index}", "url": f"https://jobs.example/roles/{index}"}
            for index in range(4)
        ]
        rows.extend(
            [
                {"title": "Missing URL"},
                {"title": "Script", "url": "https://jobs.example/roles/script", "selector": "body"},
            ]
        )

        result = normalize_smart_extract_rows(
            rows,
            source_url="https://jobs.example/careers",
            strategy="api_response",
            max_rows=3,
        )

        self.assertEqual(len(result["results"]), 3)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["rejected_count"], 2)
        self.assertTrue(all("selector" not in row for row in result["results"]))

    def test_cross_origin_result_is_retained_as_lead_not_official(self):
        result = normalize_smart_extract_rows(
            [{"title": "AI Engineer", "url": "https://ats.example/jobs/1"}],
            source_url="https://company.example/careers",
            strategy="api_response",
        )
        self.assertEqual(result["results"][0]["source_kind"], "lead")
        self.assertEqual(result["results"][0]["source_url"], "https://company.example/careers")

    def test_pinned_site_capture_uses_smart_extract_and_existing_queue(self):
        patterns = json.loads(
            (Path(__file__).parents[1] / "config" / "direct-career-sites.v1.json")
            .read_text(encoding="utf-8")
        )
        captures = [
            {
                "site_id": "startup_jobs",
                "strategy": "json_ld",
                "source_url": "https://startup.jobs/?q=AI+Engineer&remote=true",
                "rows": [
                    {
                        "@type": "JobPosting",
                        "title": "AI Engineer",
                        "url": "https://jobs.acme.example/roles/7",
                        "hiringOrganization": {"name": "Acme"},
                    }
                ],
            }
        ]
        with tempfile.TemporaryDirectory() as directory:
            queue = CandidateQueue(Path(directory) / "candidates.sqlite3")
            try:
                receipt = ingest_site_pattern_captures(
                    queue,
                    captures,
                    patterns=patterns,
                    query="AI Engineer",
                    location="Japan",
                    query_family="six_figure_japan",
                )
                pending = queue.pending(limit=10)
            finally:
                queue.close()

        self.assertEqual(receipt["inserted_count"], 1)
        self.assertEqual(receipt["accepted_row_count"], 1)
        self.assertEqual(
            pending,
            [{
                "url": "https://jobs.acme.example/roles/7",
                "source": "site_pattern:startup_jobs:smart_extract:json_ld:lead",
                "query_family": "six_figure_japan",
            }],
        )


if __name__ == "__main__":
    unittest.main()
