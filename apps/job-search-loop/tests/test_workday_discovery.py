import unittest

from job_search_loop.workday_discovery import search_workday_board


BOARD = {
    "company": "NVIDIA",
    "base_url": "https://nvidia.wd5.myworkdayjobs.com",
    "tenant": "nvidia",
    "site_id": "NVIDIAExternalCareerSite",
}


class WorkdayDiscoveryTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
