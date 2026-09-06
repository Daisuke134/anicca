import copy
import importlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import performance


class NetPerformanceTest(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads(
            (ROOT / "fixtures/net-performance.json").read_text(encoding="utf-8"))

    def test_owner_deposit_is_not_profit_and_costs_are_explicit(self):
        result = performance.project(self.fixture)
        self.assertEqual(result["measurement_status"], "measured")
        self.assertEqual(result["net_pnl_usd"], "10.00")
        self.assertEqual(result["gross_strategy_pnl_usd"], "13.00")
        self.assertEqual(result["fees_usd"], "2.00")
        self.assertEqual(result["slippage_usd"], "1.00")
        self.assertEqual(result["max_drawdown_usd"], "10.00")
        self.assertEqual(result["gross_exposure_usd"], "40.00")
        self.assertEqual(result["benchmark_pnl_usd"], "5.00")
        self.assertEqual(result["alpha_pnl_usd"], "5.00")
        self.assertFalse(result["capital_expansion_allowed"])

    def test_projection_is_identical_after_module_restart(self):
        first = performance.project(self.fixture)
        restarted = importlib.reload(performance)
        self.assertEqual(restarted.project(self.fixture), first)

    def test_every_required_unknown_blocks_capital_expansion(self):
        for key in sorted(performance.REQUIRED):
            with self.subTest(key=key):
                incomplete = copy.deepcopy(self.fixture)
                incomplete.pop(key)
                result = performance.project(incomplete)
                self.assertEqual(result["measurement_status"], "blocked")
                self.assertFalse(result["capital_expansion_allowed"])
                self.assertNotIn("net_pnl_usd", result)

    def test_non_finite_negative_cost_and_impossible_peak_fail_closed(self):
        cases = (
            {"ending_nav_usd": "NaN"},
            {"fees_usd": "-0.01"},
            {"slippage_usd": "Infinity"},
            {"peak_adjusted_nav_usd": "109.99"},
            {"benchmark_start_price_usd": "0"},
            {"observed_at": "not-a-time"},
            {"period_start": "2026-09-08T00:00:00Z"},
        )
        for changes in cases:
            with self.subTest(changes=changes):
                result = performance.project({**self.fixture, **changes})
                self.assertEqual(result["measurement_status"], "blocked")
                self.assertFalse(result["capital_expansion_allowed"])


if __name__ == "__main__":
    unittest.main()
