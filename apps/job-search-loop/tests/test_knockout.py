import unittest


class KnockoutGateTests(unittest.TestCase):
    def test_unknown_compensation_is_not_rejected_but_explicit_low_jpy_max_is(self):
        from job_search_loop.knockout import assess_candidate

        unknown = assess_candidate(
            {"title": "AI Engineer", "location": "Tokyo", "description": "Build AI systems."}
        )
        low = assess_candidate(
            {
                "title": "AI Engineer",
                "location": "Tokyo",
                "description": "Annual salary range JPY 5,000,000 - JPY 7,000,000.",
            }
        )

        self.assertNotEqual(unknown["gate_status"], "rejected")
        self.assertEqual(low["gate_status"], "rejected")
        self.assertIn("compensation_max_below_jpy_8000000", low["gate_reasons"])

    def test_exact_source_spans_quote_title_location_and_description(self):
        from job_search_loop.knockout import assess_candidate

        result = assess_candidate(
            {
                "url": "https://jobs.example/one",
                "title": "AI Deployment Engineer",
                "location": "Tokyo, Japan",
                "description": "Deploy production AI systems with enterprise customers.",
            }
        )

        self.assertTrue(any("title=AI Deployment Engineer" in span for span in result["source_spans"]))
        self.assertTrue(any("location=Tokyo, Japan" in span for span in result["source_spans"]))
        self.assertTrue(any("description=Deploy production AI systems" in span for span in result["source_spans"]))

    def test_shortlist_is_bounded_and_prefers_japan_relevant_roles(self):
        from job_search_loop.knockout import shortlist_candidates

        candidates = [
            {
                "official_url": f"https://jobs.example/{index}",
                "title": "AI Deployment Engineer" if index == 19 else "Operations Manager",
                "company": "Acme",
                "location": "Tokyo, Japan" if index == 19 else "Madrid",
                "bucket": "strong_fit",
                "language": "en",
                "provider": "official",
                "description": "Build and deploy AI systems." if index == 19 else "Manage office operations.",
            }
            for index in range(20)
        ]

        shortlist = shortlist_candidates(candidates, limit=12)

        self.assertEqual(len(shortlist), 12)
        self.assertEqual(shortlist[0]["location"], "Tokyo, Japan")
        self.assertTrue(all(row["gate_status"] != "rejected" for row in shortlist))


if __name__ == "__main__":
    unittest.main()
