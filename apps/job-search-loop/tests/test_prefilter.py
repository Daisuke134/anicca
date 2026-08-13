import unittest


class DeterministicPrefilterTests(unittest.TestCase):
    def test_builds_schema_complete_deduped_candidates_without_result_duplication(self):
        from job_search_loop.prefilter import build_prefilter_result

        plan = {
            "queries": [
                {"bucket": "dream", "language": "en", "query": "AI Tokyo"},
                {"bucket": "strong_fit", "language": "ja", "query": "AI 東京"},
            ]
        }

        def search(query):
            return {
                "status": "usable",
                "results": [
                    {
                        "company": "OpenAI",
                        "title": "AI Deployment Engineer",
                        "location": "Tokyo, Japan",
                        "url": "https://jobs.ashbyhq.com/openai/role-1",
                        "canonical_url": "https://jobs.ashbyhq.com/openai/role-1",
                        "description": " ".join(
                            ["Deploy production AI systems with customers in Tokyo."]
                            * 12
                        ),
                        "compensation": {
                            "type": "annual_salary",
                            "currency": "USD",
                            "min": 120000,
                            "max": 180000,
                            "source": "official_ashby",
                        },
                        "discovery_provider": "official_ats_boards",
                    }
                ],
                "providers": [
                    {
                        "name": "official_ats_boards",
                        "status": "success",
                        "count": 1,
                        "error": None,
                    }
                ],
            }

        result = build_prefilter_result(plan, search=search)

        self.assertEqual(result["status"], "usable")
        self.assertEqual(len(result["candidates"]), 1)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["bucket"], "dream")
        self.assertEqual(candidate["japan_eligibility_evidence"], "Tokyo, Japan")
        self.assertTrue(
            any("#title=AI Deployment Engineer" in span for span in candidate["source_spans"])
        )
        self.assertTrue(
            any("#location=Tokyo" in span for span in candidate["source_spans"])
        )
        self.assertRegex(candidate["jd_fingerprint"], r"^[0-9a-f]{16}$")
        self.assertEqual(candidate["role_family"], "applied_ai")
        self.assertIsNone(candidate["compensation_min_jpy"])
        self.assertEqual(
            candidate["compensation_status"], "verified_six_figure_usd"
        )
        self.assertTrue(candidate["ranking"]["eligible"])
        self.assertGreaterEqual(candidate["ranking"]["score"], 75)
        self.assertEqual(candidate["portfolio_bucket"], "strong_fit")
        self.assertTrue(candidate["ranking_ready"])
        self.assertTrue(candidate["ranking_inputs"]["six_figure_usd_verified"])
        self.assertEqual(
            candidate["ranking_inputs"]["japan_eligible_source_span"],
            "https://jobs.ashbyhq.com/openai/role-1#location=Tokyo, Japan",
        )
        self.assertTrue(
            candidate["ranking_inputs"]["role_family_source_span"].startswith(
                "https://jobs.ashbyhq.com/openai/role-1#title="
            )
        )
        self.assertEqual(len(result["provider_results"]), 2)
        self.assertTrue(all("results" not in row for row in result["provider_results"]))

    def test_salary_unknown_is_not_ranking_ready(self):
        from job_search_loop.prefilter import build_prefilter_result

        result = build_prefilter_result(
            {
                "queries": [
                    {"bucket": "dream", "language": "en", "query": "AI Tokyo"}
                ]
            },
            search=lambda _query: {
                "results": [
                    {
                        "company": "Unknown Pay AI",
                        "title": "AI Deployment Engineer",
                        "location": "Tokyo, Japan",
                        "url": "https://jobs.example.com/unknown",
                        "description": "Deploy AI agents with enterprise customers.",
                        "discovery_provider": "official_ats_boards",
                    }
                ],
                "providers": [],
            },
        )

        candidate = result["candidates"][0]
        self.assertFalse(candidate["ranking_ready"])
        self.assertEqual(candidate["compensation_status"], "unverified")
        self.assertIn("compensation_unverified", candidate["ranking"]["reasons"])

    def test_bare_apac_remote_is_not_japan_eligible(self):
        from job_search_loop.prefilter import build_prefilter_result

        result = build_prefilter_result(
            {
                "queries": [
                    {"bucket": "dream", "language": "en", "query": "AI remote"}
                ]
            },
            search=lambda _query: {
                "results": [
                    {
                        "company": "Remote AI",
                        "title": "AI Engineer",
                        "location": "Remote, APAC",
                        "url": "https://jobs.example.com/apac",
                        "description": "Remote role in the APAC region.",
                        "compensation": {
                            "type": "annual_salary",
                            "currency": "USD",
                            "min": 150000,
                            "max": 200000,
                            "source": "official_ashby",
                        },
                        "discovery_provider": "official_ats_boards",
                    }
                ],
                "providers": [],
            },
        )

        candidate = result["candidates"][0]
        self.assertFalse(candidate["ranking_ready"])
        self.assertIn("not_available_from_japan", candidate["ranking"]["reasons"])

    def test_failed_query_is_reported_and_does_not_block_other_queries(self):
        from job_search_loop.prefilter import build_prefilter_result

        calls = []

        def search(query):
            calls.append(query)
            if query == "broken":
                raise RuntimeError("provider down")
            return {"status": "usable", "results": [], "providers": []}

        result = build_prefilter_result(
            {
                "queries": [
                    {"bucket": "dream", "language": "en", "query": "broken"},
                    {"bucket": "adjacent", "language": "en", "query": "works"},
                ]
            },
            search=search,
        )

        self.assertEqual(calls, ["broken", "works"])
        self.assertEqual(result["status"], "browser_fallback_required")
        self.assertEqual(result["blocked"], [])
        self.assertEqual(result["provider_results"][0]["status"], "failed")


if __name__ == "__main__":
    unittest.main()
