from decimal import Decimal
import unittest

from job_search_loop.mercor_work_harness import (
    WorkHarnessError,
    advance_state,
    revenue_record,
)


class MercorWorkHarnessTests(unittest.TestCase):
    def test_authorized_work_to_settled_payout_to_revenue(self):
        state = "submitted_pending_review"
        for next_state in ("selected", "contracted", "authorized_work", "work_submitted", "accepted"):
            state, _ = advance_state(
                state,
                next_state,
                evidence_ref=f"evidence://{next_state}",
            )
        state, event = advance_state(
            state,
            "paid_settled",
            evidence_ref="https://work.mercor.com/earnings#pay-1",
            payment_id="pay-1",
            settlement_status="paid",
            amount_usd="125.00",
        )
        self.assertEqual(state, "paid_settled")
        self.assertEqual(revenue_record(event), {"payment_id": "pay-1", "amount_usd": Decimal("125.00")})

    def test_revenue_requires_settled_payment_evidence(self):
        with self.assertRaises(WorkHarnessError):
            advance_state(
                "accepted",
                "paid_settled",
                evidence_ref="evidence://offer",
                payment_id="offer-1",
                settlement_status="pending",
                amount_usd="125.00",
            )
        with self.assertRaises(WorkHarnessError):
            revenue_record(
                {
                    "state": "accepted",
                    "payment_id": "offer-1",
                    "amount_usd": "125.00",
                }
            )

    def test_human_bound_work_routes_to_needs_human(self):
        state, event = advance_state(
            "contracted",
            "needs_human",
            evidence_ref="evidence://ai-prohibited-assessment",
            reason="contract_prohibits_ai_assessment",
        )
        self.assertEqual(state, "needs_human")
        self.assertEqual(event["reason"], "contract_prohibits_ai_assessment")


if __name__ == "__main__":
    unittest.main()
