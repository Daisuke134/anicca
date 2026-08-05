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
        self.assertEqual(len(result["provider_results"]), 2)
        self.assertTrue(all("results" not in row for row in result["provider_results"]))

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
