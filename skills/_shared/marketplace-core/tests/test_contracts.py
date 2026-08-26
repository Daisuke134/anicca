import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from contracts import (  # noqa: E402
    AuthorizationReceipt,
    ContractValidationError,
    ContractReceipt,
    DeliveryReceipt,
    PaymentReceipt,
    QAReceipt,
    parse_contract,
)
from ledger import normalize_event  # noqa: E402


class ContractReceiptTests(unittest.TestCase):
    def test_parses_provider_observed_accepted_contract(self):
        receipt = parse_contract(
            {
                "schema_version": 1,
                "record_type": "contract_receipt",
                "platform": "mercor",
                "work_external_id": "work-123",
                "contract_external_id": "contract-456",
                "status": "accepted",
                "terms_sha256": "a" * 64,
                "observed_at": "2026-08-26T07:00:00Z",
            }
        )

        self.assertIsInstance(receipt, ContractReceipt)
        self.assertEqual(receipt.contract_external_id, "contract-456")

    def test_parses_explicit_work_authorization(self):
        receipt = parse_contract(
            {
                "schema_version": 1,
                "record_type": "authorization_receipt",
                "platform": "mercor",
                "contract_external_id": "contract-456",
                "authorization_external_id": "authorization-789",
                "status": "authorized",
                "scope_sha256": "b" * 64,
                "observed_at": "2026-08-26T07:05:00Z",
            }
        )

        self.assertIsInstance(receipt, AuthorizationReceipt)
        self.assertEqual(receipt.status, "authorized")

    def test_parses_artifact_bound_qa_receipt(self):
        receipt = parse_contract(
            {
                "schema_version": 1,
                "record_type": "qa_receipt",
                "platform": "mercor",
                "work_external_id": "work-123",
                "qa_external_id": "qa-012",
                "status": "passed",
                "artifact_sha256": "c" * 64,
                "report_sha256": "d" * 64,
                "observed_at": "2026-08-26T07:10:00Z",
            }
        )

        self.assertIsInstance(receipt, QAReceipt)
        self.assertEqual(receipt.status, "passed")

    def test_delivery_receipt_is_bound_to_qa(self):
        receipt = parse_contract(
            {
                "schema_version": 1,
                "record_type": "delivery_receipt",
                "platform": "mercor",
                "work_external_id": "work-123",
                "delivery_external_id": "delivery-345",
                "qa_external_id": "qa-012",
                "status": "verified",
                "artifact_sha256": "c" * 64,
                "idempotency_key": "mercor:delivery-345",
                "observed_at": "2026-08-26T07:15:00Z",
            }
        )

        self.assertIsInstance(receipt, DeliveryReceipt)
        self.assertEqual(receipt.qa_external_id, "qa-012")

    def test_payment_receipt_records_verified_net(self):
        value = {
            "schema_version": 1,
            "record_type": "payment_receipt",
            "platform": "mercor",
            "work_external_id": "work-123",
            "payment_external_id": "payment-678",
            "receipt_id": "receipt-901",
            "gross_amount_minor": 10000,
            "fee_amount_minor": 1000,
            "cost_amount_minor": 500,
            "net_amount_minor": 8500,
            "currency": "USD",
            "status": "settled",
            "occurred_at": "2026-08-26T07:20:00Z",
            "observed_at": "2026-08-26T07:21:00Z",
        }

        receipt = parse_contract(value)
        self.assertIsInstance(receipt, PaymentReceipt)
        self.assertEqual(receipt.net_amount_minor, 8500)
        self.assertEqual(normalize_event(value).amount_minor, 8500)

        value["net_amount_minor"] = 9000
        with self.assertRaisesRegex(ContractValidationError, "net_amount_minor"):
            parse_contract(value)


if __name__ == "__main__":
    unittest.main()
