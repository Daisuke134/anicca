import json
import tempfile
import unittest
from pathlib import Path

from job_search_loop.ats_liveness import (
    classify_ashby_board,
    classify_workable_board,
    check_liveness_via_api,
    resolve_ats_api,
    sweep_candidate_queue,
    write_liveness_receipt,
)
from job_search_loop.candidate_queue import CandidateQueue


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

    def test_per_job_200_is_active_and_request_refuses_redirects(self):
        calls = []

        def request(url, *, timeout_seconds, follow_redirects):
            calls.append((url, timeout_seconds, follow_redirects))
            return 200, {"id": 12345}

        result = check_liveness_via_api(
            "https://job-boards.greenhouse.io/acme/jobs/12345",
            request=request,
        )

        self.assertEqual(result["result"], "active")
        self.assertEqual(result["code"], "greenhouse_api_ok")
        self.assertEqual(calls[0][2], False)
        self.assertGreater(calls[0][1], 0)

    def test_exact_gone_status_is_expired(self):
        for status in (404, 410):
            with self.subTest(status=status):
                result = check_liveness_via_api(
                    "https://jobs.lever.co/acme/abc-123",
                    request=lambda *_args, **_kwargs: (status, None),
                )
                self.assertEqual(result["result"], "expired")
                self.assertEqual(result["code"], "lever_api_gone")

    def test_ambiguous_status_parse_drift_and_network_error_remain_pending(self):
        for response in ((302, None), (429, None), (500, None), (200, "changed")):
            with self.subTest(response=response):
                self.assertIsNone(
                    check_liveness_via_api(
                        "https://jobs.ashbyhq.com/acme/abc-123",
                        request=lambda *_args, **_kwargs: response,
                    )
                )

        def failed_request(*_args, **_kwargs):
            raise TimeoutError("bounded timeout")

        self.assertIsNone(
            check_liveness_via_api(
                "https://jobs.lever.co/acme/abc-123",
                request=failed_request,
            )
        )

    def test_receipt_hashes_url_and_is_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "liveness.json"
            raw_url = "https://jobs.lever.co/acme/abc-123"
            write_liveness_receipt(
                output,
                raw_url,
                {"result": "active", "code": "lever_api_ok", "reason": "live"},
            )
            receipt_text = output.read_text(encoding="utf-8")
            receipt = json.loads(receipt_text)
            self.assertNotIn(raw_url, receipt_text)
            self.assertEqual(len(receipt["url_sha256"]), 64)
            self.assertEqual(receipt["result"], "active")
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)

    def test_sweep_rejects_only_expired_and_keeps_active_or_uncertain_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            database = root / "candidate.sqlite3"
            evidence = root / "evidence"
            queue = CandidateQueue(database)
            urls = {
                "https://jobs.lever.co/acme/live": "active",
                "https://jobs.lever.co/acme/gone": "expired",
                "https://jobs.lever.co/acme/uncertain": None,
                "https://example.com/browser-only": "ignored",
            }
            queue.discover(
                {"url": url, "source": "test", "query_family": "test"}
                for url in urls
            )
            queue.close()

            def check(url):
                outcome = urls[url]
                if outcome is None:
                    return None
                return {
                    "result": outcome,
                    "code": f"lever_api_{outcome}",
                    "reason": outcome,
                }

            receipt = sweep_candidate_queue(
                database,
                evidence,
                limit=10,
                check=check,
            )

            self.assertEqual(receipt["api_supported_count"], 3)
            self.assertEqual(receipt["active_count"], 1)
            self.assertEqual(receipt["expired_count"], 1)
            self.assertEqual(receipt["inconclusive_count"], 1)
            queue = CandidateQueue(database)
            self.assertEqual(queue.summary()["remaining_unverified_count"], 3)
            queue.close()
            evidence_text = "".join(
                path.read_text(encoding="utf-8") for path in evidence.glob("*.json")
            )
            self.assertNotIn("jobs.lever.co", evidence_text)
            self.assertEqual(len(list(evidence.glob("*.json"))), 3)


if __name__ == "__main__":
    unittest.main()
