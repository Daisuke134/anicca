import unittest

from job_search_loop.compensation import CompensationError, classify_six_figure_usd


class CompensationTests(unittest.TestCase):
    def setUp(self):
        self.rate = {
            "provider": "Bank of Japan",
            "release_url": "https://www.boj.or.jp/en/statistics/market/forex/fxdaily/fxlist/fx260804.pdf",
            "observation_date": "2026-08-04",
            "observation_time_jst": "17:00",
            "usd_jpy_bid": "157.80",
            "usd_jpy_offer": "157.82",
            "release_sha256": "1a01ed907a2941ebc19e2e6987029c390d0b661109d33690c812c7ada0f7abb8",
        }

    def test_six_figure_classification_requires_value_currency_rate_and_timestamp(self):
        receipt = classify_six_figure_usd(
            value="15781000",
            currency="JPY",
            value_kind="annual_base",
            rate_evidence=self.rate,
        )
        self.assertEqual(receipt["converted_usd"], "100000.00")
        self.assertEqual(receipt["usd_jpy_mid"], "157.81")
        self.assertTrue(receipt["six_figure_usd"])
        self.assertEqual(receipt["rate_observed_at"], "2026-08-04T17:00:00+09:00")
        self.assertEqual(len(receipt["receipt_sha256"]), 64)

        below = classify_six_figure_usd(
            value="15780999",
            currency="JPY",
            value_kind="annual_total_compensation",
            rate_evidence=self.rate,
        )
        self.assertFalse(below["six_figure_usd"])
        for missing in ("value", "currency", "observation_date", "usd_jpy_bid"):
            evidence = dict(self.rate)
            kwargs = {
                "value": "15781000",
                "currency": "JPY",
                "value_kind": "annual_base",
                "rate_evidence": evidence,
            }
            if missing in kwargs:
                kwargs[missing] = None
            else:
                evidence.pop(missing)
            with self.assertRaises(CompensationError, msg=missing):
                classify_six_figure_usd(**kwargs)

    def test_non_boj_or_non_annual_or_non_1700_evidence_fails_closed(self):
        cases = []
        for key, value in (
            ("release_url", "https://example.com/rate.pdf"),
            ("observation_time_jst", "09:00"),
            ("provider", "Example FX"),
        ):
            evidence = dict(self.rate)
            evidence[key] = value
            cases.append(evidence)
        for evidence in cases:
            with self.assertRaises(CompensationError):
                classify_six_figure_usd(
                    value="15781000",
                    currency="JPY",
                    value_kind="annual_base",
                    rate_evidence=evidence,
                )
        with self.assertRaises(CompensationError):
            classify_six_figure_usd(
                value="15781000",
                currency="JPY",
                value_kind="monthly_base",
                rate_evidence=self.rate,
            )


if __name__ == "__main__":
    unittest.main()
