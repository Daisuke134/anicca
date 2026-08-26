import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from contracts import (  # noqa: E402
    AuthorizationReceipt,
    ContractReceipt,
    QAReceipt,
    parse_contract,
)


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


if __name__ == "__main__":
    unittest.main()
