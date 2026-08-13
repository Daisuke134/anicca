import tempfile
import unittest
from pathlib import Path

from job_search_loop.official_ats_boards import search_official_boards


class OfficialAtsBoardsTests(unittest.TestCase):
    def test_fetches_and_normalizes_ashby_and_greenhouse_boards(self):
        boards = [
            {"company": "OpenAI", "ats": "ashby", "slug": "openai"},
            {"company": "Anthropic", "ats": "greenhouse", "slug": "anthropic"},
        ]
        calls = []

        def request(url, *, timeout_seconds, follow_redirects):
            calls.append((url, timeout_seconds, follow_redirects))
            if "ashbyhq" in url:
                return {
                    "jobs": [
                        {
                            "id": "ash-1",
                            "title": "AI Agent Engineer",
                            "jobUrl": "https://jobs.ashbyhq.com/openai/ash-1",
                            "location": "Tokyo",
                            "publishedAt": "2026-08-01T00:00:00Z",
                            "isListed": True,
                            "isRemote": True,
                            "workplaceType": "Remote",
                            "secondaryLocations": [{"location": "Japan"}],
                            "compensation": {
                                "summaryComponents": [
                                    {
                                        "compensationType": "Salary",
                                        "interval": "1 YEAR",
                                        "currencyCode": "USD",
                                        "minValue": 120000,
                                        "maxValue": 180000,
                                    }
                                ]
                            },
                        }
                    ]
                }
            return {
                "jobs": [
                    {
                        "id": 123,
                        "title": "Research Engineer, Agents",
                        "absolute_url": "https://job-boards.greenhouse.io/anthropic/jobs/123",
                        "location": {"name": "Remote - Japan"},
                        "first_published": "2026-08-02T00:00:00Z",
                    }
                ]
            }

        rows = search_official_boards(
            "AI agents Japan",
            boards=boards,
            request=request,
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual({row["company"] for row in rows}, {"OpenAI", "Anthropic"})
        self.assertTrue(all(row["source_kind"] == "official" for row in rows))
        self.assertTrue(all(call[2] is False for call in calls))
        self.assertIn(
            "content=true", next(url for url, *_ in calls if "greenhouse" in url)
        )
        ashby = next(row for row in rows if row["company"] == "OpenAI")
        self.assertEqual(ashby["compensation"]["min"], 120000)
        self.assertEqual(ashby["secondary_locations"], ["Japan"])
        self.assertTrue(ashby["is_remote"])

    def test_unlisted_ashby_and_malformed_rows_are_dropped(self):
        rows = search_official_boards(
            "AI",
            boards=[{"company": "Acme", "ats": "ashby", "slug": "acme"}],
            request=lambda *_args, **_kwargs: {
                "jobs": [
                    {"id": "hidden", "title": "AI", "jobUrl": "https://jobs.ashbyhq.com/acme/hidden", "isListed": False},
                    {"id": "missing-url", "title": "AI", "isListed": True},
                ]
            },
        )
        self.assertEqual(rows, [])

    def test_private_cache_avoids_refetch_within_ttl(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "boards.json"
            calls = []

            def request(*_args, **_kwargs):
                calls.append(1)
                return {
                    "jobs": [
                        {
                            "id": "one",
                            "title": "AI Engineer",
                            "jobUrl": "https://jobs.ashbyhq.com/acme/one",
                            "isListed": True,
                        }
                    ]
                }

            kwargs = {
                "boards": [{"company": "Acme", "ats": "ashby", "slug": "acme"}],
                "request": request,
                "cache_path": cache,
                "cache_ttl_seconds": 900,
            }
            self.assertEqual(len(search_official_boards("AI", **kwargs)), 1)
            self.assertEqual(len(search_official_boards("Engineer", **kwargs)), 1)
            self.assertEqual(len(calls), 1)
            self.assertEqual(cache.stat().st_mode & 0o777, 0o600)

    def test_caps_results_and_prioritizes_title_plus_japan_location(self):
        jobs = [
            {
                "id": f"job-{index}",
                "title": "AI Engineer" if index else "AI Agent Engineer",
                "jobUrl": f"https://jobs.ashbyhq.com/acme/job-{index}",
                "location": "Remote" if index else "Tokyo, Japan",
                "isListed": True,
            }
            for index in range(150)
        ]
        rows = search_official_boards(
            "AI agent engineer Japan remote",
            boards=[{"company": "Acme", "ats": "ashby", "slug": "acme"}],
            request=lambda *_args, **_kwargs: {"jobs": jobs},
        )
        self.assertEqual(len(rows), 25)
        self.assertEqual(rows[0]["location"], "Tokyo, Japan")

    def test_query_output_truncates_description_for_bounded_model_context(self):
        rows = search_official_boards(
            "AI",
            boards=[{"company": "Acme", "ats": "ashby", "slug": "acme"}],
            request=lambda *_args, **_kwargs: {
                "jobs": [
                    {
                        "title": "AI Engineer",
                        "jobUrl": "https://jobs.ashbyhq.com/acme/one",
                        "descriptionPlain": "x" * 2_000,
                        "isListed": True,
                    }
                ]
            },
        )

        self.assertEqual(len(rows[0]["description"]), 500)


if __name__ == "__main__":
    unittest.main()
