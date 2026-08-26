from decimal import Decimal
import unittest

from job_search_loop.mercor_work_harness import (
    WorkHarnessError,
    advance_state,
    revenue_record,
)


class MercorWorkHarnessTests(unittest.TestCase):
    def test_authorized_work_to_bank_matched_revenue(self):
        state = "submitted_pending_review"
        for next_state in ("selected", "contracted", "authorized_work", "work_submitted", "accepted"):
            kwargs = {}
            if next_state == "authorized_work":
                kwargs["authorization_policy"] = "explicitly_allowed"
            if next_state == "accepted":
                kwargs["acceptance_status"] = "accepted"
            state, _ = advance_state(
                state,
                next_state,
                evidence_ref=f"evidence://{next_state}",
                **kwargs,
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
        with self.assertRaises(WorkHarnessError):
            revenue_record(event)
        state, bank = advance_state(
            state,
            "bank_matched",
            evidence_ref="bank://transaction-1",
            payment_id="pay-1",
            payout_id="payout-1",
            bank_transaction_id="transaction-1",
            match_status="matched",
            amount_usd="125.00",
        )
        self.assertEqual(state, "bank_matched")
        self.assertEqual(
            revenue_record(bank),
            {
                "payment_id": "pay-1",
                "payout_id": "payout-1",
                "bank_transaction_id": "transaction-1",
                "amount_usd": Decimal("125.00"),
            },
        )

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
                    "state": "paid_settled",
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

    def test_authorized_work_requires_explicit_ai_permission_and_acceptance_proof(self):
        with self.assertRaises(WorkHarnessError):
            advance_state("contracted", "authorized_work", evidence_ref="contract://1")
        state, _ = advance_state(
            "contracted",
            "authorized_work",
            evidence_ref="contract://1",
            authorization_policy="explicitly_allowed",
        )
        with self.assertRaises(WorkHarnessError):
            advance_state("work_submitted", "accepted", evidence_ref="acceptance://1")
        state, event = advance_state(
            "work_submitted",
            "accepted",
            evidence_ref="acceptance://1",
            acceptance_status="accepted",
        )
        self.assertEqual(state, "accepted")
        self.assertEqual(event["acceptance_status"], "accepted")


if __name__ == "__main__":
    unittest.main()
