import unittest

from job_search_loop.ats_liveness import (
    classify_ashby_board,
    classify_workable_board,
    resolve_ats_api,
)


class AtsLivenessTests(unittest.TestCase):
    def test_resolves_supported_posting_urls_to_fixed_public_api_hosts(self):
        cases = {
            "https://job-boards.greenhouse.io/acme/jobs/12345": (
                "greenhouse",
                "https://boards-api.greenhouse.io/v1/boards/acme/jobs/12345",
            ),
            "https://jobs.eu.lever.co/acme/abc-123": (
                "lever",
                "https://api.eu.lever.co/v0/postings/acme/abc-123",
            ),
            "https://jobs.ashbyhq.com/acme/abc-123/application": (
                "ashby",
                "https://api.ashbyhq.com/posting-api/job-board/acme",
            ),
            "https://acme.wd5.myworkdayjobs.com/en-US/site/job/Tokyo/AI-Engineer_R1": (
                "workday",
                "https://acme.wd5.myworkdayjobs.com/wday/cxs/acme/site/job/Tokyo/AI-Engineer_R1",
            ),
            "https://apply.workable.com/acme/j/ABC123/": (
                "workable",
                "https://apply.workable.com/api/v1/widget/accounts/acme?details=true",
            ),
        }
        for url, expected in cases.items():
            with self.subTest(url=url):
                resolved = resolve_ats_api(url)
                self.assertIsNotNone(resolved)
                self.assertEqual((resolved.ats, resolved.api_url), expected)

    def test_rejects_non_https_traversal_and_lookalike_hosts(self):
        urls = [
            "http://jobs.ashbyhq.com/acme/job",
            "https://jobs.ashbyhq.com.evil.test/acme/job",
            "https://jobs.ashbyhq.com/acme/../job",
            "https://evil.test/acme.wd5.myworkdayjobs.com/site/job/Tokyo/R1",
            "https://apply.workable.com/acme%2F..%2Fevil/j/ABC123/",
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertIsNone(resolve_ats_api(url))

    def test_ashby_board_requires_exact_listed_job(self):
        payload = {"jobs": [{"id": "ABC-123", "isListed": True}]}
        self.assertEqual(classify_ashby_board(payload, "abc-123")["result"], "active")
        self.assertEqual(classify_ashby_board(payload, "missing")["result"], "expired")
        self.assertIsNone(classify_ashby_board({"jobs": "changed"}, "abc-123"))

    def test_workable_board_requires_exact_shortcode_or_posting_url(self):
        payload = {
            "jobs": [
                {
                    "shortcode": "ABC123",
                    "url": "https://apply.workable.com/acme/j/ABC123/",
                }
            ]
        }
        self.assertEqual(classify_workable_board(payload, "ABC123")["result"], "active")
        self.assertEqual(classify_workable_board(payload, "MISSING")["result"], "expired")
        self.assertIsNone(classify_workable_board({"jobs": None}, "ABC123"))


if __name__ == "__main__":
    unittest.main()
