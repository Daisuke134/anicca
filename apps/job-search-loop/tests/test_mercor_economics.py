from decimal import Decimal
import unittest

from job_search_loop.mercor_economics import monthly_gross_projection


class MercorEconomicsTests(unittest.TestCase):
    def test_capacity_capped_projection_does_not_multiply_jobs(self):
        result = monthly_gross_projection(
            rate_min_usd=80,
            rate_max_usd=120,
            weekly_hours=40,
            accepted_application_count=3,
        )
        self.assertEqual(result["gross_min_usd"], Decimal("13866.67"))
        self.assertEqual(result["gross_max_usd"], Decimal("20800.00"))
        self.assertEqual(result["capacity_capped"], True)
        self.assertEqual(result["revenue_status"], "projection_only")
        self.assertEqual(result["naive_three_full_time_min_usd"], Decimal("41600.00"))

    def test_weekly_hours_are_bounded(self):
        with self.assertRaises(ValueError):
            monthly_gross_projection(80, 120, 81, 1)


if __name__ == "__main__":
    unittest.main()
