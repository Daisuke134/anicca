import unittest


class PortfolioTests(unittest.TestCase):
    def classify(self, **values):
        try:
            from job_search_loop.portfolio import classify_portfolio
        except ImportError:
            self.fail("job_search_loop.portfolio is missing")
        return classify_portfolio(**values)

    def test_exceptional_score_is_dream(self):
        self.assertEqual(
            self.classify(
                score=95,
                compensation_min_jpy=10_000_000,
                role_family="applied_ai",
            ),
            "dream",
        )

    def test_exceptional_compensation_is_dream(self):
        self.assertEqual(
            self.classify(
                score=82,
                compensation_min_jpy=20_000_000,
                role_family="ai_partnerships",
            ),
            "dream",
        )

    def test_technical_business_role_is_adjacent(self):
        self.assertEqual(
            self.classify(
                score=82,
                compensation_min_jpy=10_000_000,
                role_family="technical_account_management",
            ),
            "adjacent",
        )

    def test_core_ai_role_is_strong_fit(self):
        self.assertEqual(
            self.classify(
                score=82,
                compensation_min_jpy=10_000_000,
                role_family="applied_ai",
            ),
            "strong_fit",
        )

    def test_ineligible_score_cannot_be_classified(self):
        with self.assertRaisesRegex(ValueError, "eligible score"):
            self.classify(
                score=74,
                compensation_min_jpy=30_000_000,
                role_family="applied_ai",
            )
