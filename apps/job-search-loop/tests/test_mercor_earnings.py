from decimal import Decimal
import unittest

from job_search_loop.mercor_earnings import (
    EarningsReadbackError,
    build_earnings_result,
)


class MercorEarningsTests(unittest.TestCase):
    def test_only_paid_rows_count_and_run_rate_uses_settled_amounts(self):
        result = build_earnings_result(
            {
                "provider": "mercor",
                "page_url": "https://work.mercor.com/earnings",
                "observed_at": "2026-08-22T11:00:00+00:00",
                "total_earnings_usd": "125.00",
                "payment_history_status": "has_rows",
                "rows": [
                    {
                        "payment_id": "pay-1",
                        "status": "Paid",
                        "earned_usd": "125.00",
                        "payout_date": "2026-08-20",
                    },
                    {
                        "payment_id": "pay-pending",
                        "status": "Pending",
                        "earned_usd": "9000.00",
                        "payout_date": "2026-08-21",
                    },
                ],
            }
        )

        self.assertEqual(result["status"], "settled")
        self.assertEqual(result["settled_total_usd"], Decimal("125.00"))
        self.assertEqual(result["verified_monthly_run_rate_usd"], Decimal("125.00"))
        self.assertEqual([row["payment_id"] for row in result["settled_rows"]], ["pay-1"])

    def test_empty_payment_history_is_not_observed_not_zero_revenue(self):
        result = build_earnings_result(
            {
                "provider": "mercor",
                "page_url": "https://work.mercor.com/earnings",
                "observed_at": "2026-08-22T11:00:00+00:00",
                "total_earnings_usd": "0.00",
                "payment_history_status": "empty",
                "rows": [],
            }
        )

        self.assertEqual(result["status"], "not_observed")
        self.assertEqual(result["settled_rows"], [])
        self.assertIsNone(result["verified_monthly_run_rate_usd"])

    def test_invalid_provider_and_settled_row_fail_closed(self):
        with self.assertRaises(EarningsReadbackError):
            build_earnings_result(
                {
                    "provider": "other",
                    "page_url": "https://work.mercor.com/earnings",
                    "observed_at": "2026-08-22T11:00:00+00:00",
                    "payment_history_status": "empty",
                    "rows": [],
                }
            )
        with self.assertRaises(EarningsReadbackError):
            build_earnings_result(
                {
                    "provider": "mercor",
                    "page_url": "https://work.mercor.com/earnings",
                    "observed_at": "2026-08-22T11:00:00+00:00",
                    "payment_history_status": "has_rows",
                    "rows": [
                        {
                            "payment_id": "pay-bad",
                            "status": "Paid",
                            "earned_usd": "-1.00",
                            "payout_date": "2026-08-20",
                        }
                    ],
                }
            )


if __name__ == "__main__":
    unittest.main()
