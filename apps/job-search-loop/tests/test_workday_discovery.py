import json
import tempfile
import unittest
from pathlib import Path

from job_search_loop.candidate_queue import CandidateQueue
from job_search_loop.workday_discovery import ingest_workday_boards, search_workday_board


BOARD = {
    "company": "NVIDIA",
    "base_url": "https://nvidia.wd5.myworkdayjobs.com",
    "tenant": "nvidia",
    "site_id": "NVIDIAExternalCareerSite",
}


class WorkdayDiscoveryTests(unittest.TestCase):
    def test_registry_is_pinned_to_applypilot_and_contains_global_employers(self):
        registry = json.loads(
            (Path(__file__).resolve().parents[1] / "config" / "workday-boards.v1.json").read_text(encoding="utf-8")
        )
        self.assertEqual(registry["source"]["commit"], "4a8d521f67f5139811c0a910ef37410f8e6d836a")
        self.assertEqual(registry["source"]["blob_sha"], "528732e7bebdc0541b538d6e95590e4b651e399b")
        self.assertEqual(
            {board["company"] for board in registry["boards"]},
            {"Adobe", "Cisco", "Intel", "Mastercard", "NVIDIA", "PayPal", "Salesforce", "Uber", "Workday"},
        )

    def test_posts_bounded_pages_and_emits_direct_official_urls(self):
        calls = []

        def request(url, *, payload, timeout_seconds, follow_redirects):
            calls.append((url, payload, timeout_seconds, follow_redirects))
            offset = payload["offset"]
            postings = {
                0: [
                    {"title": "AI Solutions Architect", "locationsText": "Tokyo, Japan", "externalPath": "/job/Tokyo/AI-Solutions-Architect_R1"},
                    {"title": "AI Engineer", "locationsText": "Remote, Japan", "externalPath": "/job/Japan/AI-Engineer_R2"},
                ],
                2: [
                    {"title": "Developer Relations", "locationsText": "Japan", "externalPath": "/job/Japan/Developer-Relations_R3"},
                ],
            }.get(offset, [])
            return {"total": 3, "jobPostings": postings}

        result = search_workday_board(
            "AI Japan",
            board=BOARD,
            request=request,
            page_size=2,
            max_pages=2,
            max_results=3,
        )

        self.assertEqual([call[1]["offset"] for call in calls], [0, 2])
        self.assertTrue(all(call[0].endswith("/wday/cxs/nvidia/NVIDIAExternalCareerSite/jobs") for call in calls))
        self.assertTrue(all(call[2] == 12.0 and call[3] is False for call in calls))
        self.assertEqual(len(result["results"]), 3)
        self.assertEqual(result["results"][0]["source_kind"], "official")
        self.assertEqual(result["results"][0]["ats"], "workday")
        self.assertEqual(
            result["results"][0]["url"],
            "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite/job/Tokyo/AI-Solutions-Architect_R1",
        )

    def test_rejects_non_workday_hosts_before_request(self):
        with self.assertRaisesRegex(ValueError, "Workday host"):
            search_workday_board(
                "AI",
                board={**BOARD, "base_url": "https://myworkdayjobs.com.evil.example"},
                request=lambda *_args, **_kwargs: self.fail("request must not run"),
            )

    def test_inactive_and_malformed_postings_are_classified_not_emitted(self):
        result = search_workday_board(
            "AI",
            board=BOARD,
            request=lambda *_args, **_kwargs: {
                "total": 3,
                "jobPostings": [
                    {"title": "Closed role", "externalPath": "/job/closed", "isListed": False},
                    {"title": "Missing path"},
                    {"title": "Escaped path", "externalPath": "https://evil.example/job"},
                ],
            },
        )

        self.assertEqual(result["results"], [])
        self.assertEqual(result["inactive_count"], 1)
        self.assertEqual(result["malformed_count"], 2)

    def test_registry_results_use_existing_queue_and_restart_replay_is_idempotent(self):
        def request(_url, *, payload, **_kwargs):
            return {
                "total": 2,
                "jobPostings": [
                    {"title": "AI Engineer", "externalPath": "/job/Japan/AI-Engineer_R1", "locationsText": "Tokyo"},
                    {"title": "Closed", "externalPath": "/job/closed", "isListed": False},
                ],
            }

        with tempfile.TemporaryDirectory() as directory:
            queue = CandidateQueue(Path(directory) / "candidates.sqlite3")
            try:
                first = ingest_workday_boards(
                    queue, "AI Japan", query_family="six_figure_japan", boards=[BOARD], request=request
                )
                replay = ingest_workday_boards(
                    queue, "AI Japan", query_family="six_figure_japan", boards=[BOARD], request=request
                )
                pending = queue.pending(limit=10)
            finally:
                queue.close()

        self.assertEqual(first["inserted_count"], 1)
        self.assertEqual(first["inactive_count"], 1)
        self.assertEqual(replay["inserted_count"], 0)
        self.assertEqual(replay["duplicate_count"], 1)
        self.assertEqual(pending[0]["source"], "official_workday:NVIDIA")


if __name__ == "__main__":
    unittest.main()
