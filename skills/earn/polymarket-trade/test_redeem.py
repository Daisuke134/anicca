#!/usr/bin/env python3
"""RED->GREEN tests for redeem.py's pure functions (no network, no chain, no relayer).

Run: python3 test_redeem.py   (stdlib unittest only — no pytest install required)
"""
from __future__ import annotations
import unittest

from redeem import (
    dedupe_redeemable_conditions,
    classify_market_type,
    compute_recovered_amount,
    build_ledger_line,
)


class TestDedupeRedeemableConditions(unittest.TestCase):
    def test_merges_two_outcome_rows_sharing_one_condition(self):
        # Wimbledon: same conditionId appears twice (winning Flavio leg $10, losing
        # Karen leg $0) — must collapse into ONE row summing currentValue.
        positions = [
            {"conditionId": "0xc8a0", "title": "Wimbledon", "negativeRisk": False,
             "currentValue": 10, "initialValue": 3.55, "cashPnl": 6.45, "redeemable": True},
            {"conditionId": "0xc8a0", "title": "Wimbledon", "negativeRisk": False,
             "currentValue": 0, "initialValue": 3.55, "cashPnl": -3.55, "redeemable": True},
        ]
        rows = dedupe_redeemable_conditions(positions)
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0]["currentValue"], 10)
        self.assertAlmostEqual(rows[0]["initialValue"], 7.10)

    def test_skips_non_redeemable_positions(self):
        positions = [
            {"conditionId": "0xopen", "title": "Still open", "negativeRisk": False,
             "currentValue": 5, "initialValue": 4, "cashPnl": 1, "redeemable": False},
        ]
        self.assertEqual(dedupe_redeemable_conditions(positions), [])

    def test_keeps_distinct_conditions_separate(self):
        positions = [
            {"conditionId": "0xa", "title": "A", "negativeRisk": True,
             "currentValue": 6.7857, "initialValue": 3.7999, "cashPnl": 2.9857, "redeemable": True},
            {"conditionId": "0xb", "title": "B", "negativeRisk": False,
             "currentValue": 5, "initialValue": 3.65, "cashPnl": 1.35, "redeemable": True},
        ]
        rows = dedupe_redeemable_conditions(positions)
        self.assertEqual({r["conditionId"] for r in rows}, {"0xa", "0xb"})

    def test_sorted_by_currentValue_descending(self):
        positions = [
            {"conditionId": "0xsmall", "title": "small", "negativeRisk": False,
             "currentValue": 1, "initialValue": 1, "cashPnl": 0, "redeemable": True},
            {"conditionId": "0xbig", "title": "big", "negativeRisk": False,
             "currentValue": 10, "initialValue": 1, "cashPnl": 9, "redeemable": True},
        ]
        rows = dedupe_redeemable_conditions(positions)
        self.assertEqual([r["conditionId"] for r in rows], ["0xbig", "0xsmall"])


class TestClassifyMarketType(unittest.TestCase):
    def test_neg_risk_true(self):
        self.assertEqual(classify_market_type(True), "neg_risk")

    def test_neg_risk_false(self):
        self.assertEqual(classify_market_type(False), "standard")


class TestComputeRecoveredAmount(unittest.TestCase):
    def test_positive_delta(self):
        self.assertAlmostEqual(compute_recovered_amount(0.2411, 21.79), 21.5489, places=4)

    def test_zero_delta(self):
        self.assertEqual(compute_recovered_amount(5.0, 5.0), 0.0)

    def test_negative_delta_raises(self):
        # R4 guardrail: money must never appear to leave this wallet during a redeem.
        with self.assertRaises(ValueError):
            compute_recovered_amount(10.0, 9.0)


class TestBuildLedgerLine(unittest.TestCase):
    def test_fields_match_earn_ledger_schema(self):
        row = {
            "conditionId": "0xa947b7c6",
            "title": "Will Morocco win on 2026-07-04?",
            "negativeRisk": True,
            "currentValue": 6.7857,
            "initialValue": 3.7999,
            "cashPnl": 2.9857,
        }
        line = build_ledger_line(row, tx_hash="0xdeadbeef", status="0x1")
        self.assertEqual(line["source"], "polymarket-redeem")
        self.assertEqual(line["tx"], "0xdeadbeef")
        self.assertEqual(line["status"], "0x1")
        self.assertEqual(line["chain"], "polygon")
        self.assertTrue(line["external"])
        self.assertAlmostEqual(line["earn_usdc"], 6.7857)
        self.assertAlmostEqual(line["cost_usdc"], 3.7999)


if __name__ == "__main__":
    unittest.main()
