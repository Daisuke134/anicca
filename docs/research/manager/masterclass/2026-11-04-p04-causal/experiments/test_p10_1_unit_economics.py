"""Contract checks for P10-1 synthetic ledger projection."""
from __future__ import annotations
import unittest
from dataclasses import replace

from p10_1_unit_economics import Event, Work, demo, summarize


class P10OneLedgerTest(unittest.TestCase):
    def setUp(self):
        self.works, self.events = demo()

    def test_total_margin(self):
        r = summarize(self.works, self.events)
        self.assertEqual(r["verified_financials"]["revenue_minor"], 500)
        self.assertEqual(r["verified_financials"]["cost_minor"], 330)
        self.assertEqual(r["verified_financials"]["contribution_margin_minor"], 170)

    def test_success_cost_includes_failure_and_no_action(self):
        r = summarize(self.works, self.events)
        self.assertEqual(r["verified_financials"]["cost_per_verified_success_minor"], "330")
        self.assertEqual(r["verified_success_count"], 1)

    def test_human_assist_is_counted(self):
        r = summarize(self.works, self.events)
        self.assertEqual(r["human_assisted_work_count"], 1)
        self.assertEqual(r["human_seconds_total"], 120)
        self.assertEqual(r["per_work"][1]["margin_minor"], -230)

    def test_welfare_never_inferred_from_profit(self):
        r = summarize(self.works, self.events)
        self.assertTrue(all(x["benefit_state"] == "NOT_MEASURED" for x in r["per_work"]))

    def test_duplicate_event_id_fails(self):
        with self.assertRaisesRegex(ValueError, "duplicate event_id"):
            summarize(self.works, self.events + [replace(self.events[0], provider_event_id="new")])

    def test_duplicate_provider_event_id_fails(self):
        with self.assertRaisesRegex(ValueError, "duplicate provider_event_id"):
            summarize(self.works, self.events + [replace(self.events[0], event_id="new")])

    def test_unallocated_cost_fails(self):
        with self.assertRaisesRegex(ValueError, "unallocated"):
            summarize(self.works, self.events + [
                replace(self.events[0], event_id="unknown", provider_event_id="unknown",
                        work_item_id="MISSING", kind="tool")])

    def test_negative_money_fails(self):
        with self.assertRaisesRegex(ValueError, "nonnegative"):
            summarize(self.works, [replace(self.events[0], amount_minor=-1)] + self.events[1:])

    def test_foreign_currency_fails(self):
        with self.assertRaisesRegex(ValueError, "USD"):
            summarize(self.works, [replace(self.events[0], currency="JPY")] + self.events[1:])

    def test_estimated_revenue_fails(self):
        with self.assertRaisesRegex(ValueError, "estimated revenue"):
            summarize(self.works, [replace(self.events[0], evidence_tier="ESTIMATED")] + self.events[1:])

    def test_missing_financial_coverage_not_zero(self):
        works = [replace(self.works[0], cost_coverage_complete=False)] + self.works[1:]
        r = summarize(works, self.events)
        self.assertFalse(r["all_financial_coverage_complete"])
        self.assertIsNone(r["verified_financials"]["contribution_margin_minor"])
        self.assertEqual(r["per_work"][0]["financial_status"], "INCOMPLETE")

    def test_no_verified_success_no_divide_by_zero(self):
        works = [replace(x, state="NO_ACTION") for x in self.works]
        r = summarize(works, self.events)
        self.assertIsNone(r["verified_financials"]["cost_per_verified_success_minor"])

    def test_no_self_verified_success(self):
        works = [replace(self.works[0], outcome_source_ref=None)] + self.works[1:]
        with self.assertRaisesRegex(ValueError, "independent source"):
            summarize(works, self.events)

    def test_duplicate_work_id_fails(self):
        with self.assertRaisesRegex(ValueError, "duplicate work_item"):
            summarize(self.works+[self.works[0]], self.events)

    def test_invalid_money_type_fails(self):
        with self.assertRaisesRegex(ValueError, "integer"):
            summarize(self.works, [replace(self.events[0], amount_minor=5.5)] + self.events[1:])


if __name__ == "__main__":
    unittest.main()
