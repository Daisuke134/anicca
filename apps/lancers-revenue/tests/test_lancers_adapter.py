import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADAPTER_PATH = REPO_ROOT / "skills/earn/lancers/scripts/lancers_adapter.py"


def _load():
    spec = importlib.util.spec_from_file_location("test_lancers_adapter", ADAPTER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("lancers_adapter_unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class LancersReceiptAdapterTests(unittest.TestCase):
    def test_maps_escrow_confirmed_project_to_contract_receipt(self):
        adapter = _load()

        receipt = adapter.normalize_contract_receipt(
            {
                "source_kind": "project",
                "project_id": "123",
                "proposal_id": "456",
                "status": "進行中",
                "funding_status": "escrow_confirmed",
                "price_jpy": 10000,
                "delivery_due_on": "2026-09-01",
                "proposal_text": "検証済みの提案本文",
            },
            observed_at="2026-08-26T08:00:00Z",
        )

        self.assertEqual(receipt["record_type"], "contract_receipt")
        self.assertEqual(receipt["application_external_id"], "456")
        self.assertEqual(receipt["contract_external_id"], "project:123")
        self.assertEqual(receipt["status"], "accepted")

    def test_rejects_candidate_without_escrow_readback(self):
        adapter = _load()

        with self.assertRaisesRegex(adapter.LancersProjectError, "contract_funding_unverified"):
            adapter.normalize_contract_receipt(
                {
                    "source_kind": "project",
                    "project_id": "123",
                    "proposal_id": "456",
                    "status": "進行中",
                    "funding_status": "requires_detail_readback",
                    "price_jpy": 10000,
                    "delivery_due_on": "2026-09-01",
                    "proposal_text": "検証済みの提案本文",
                },
                observed_at="2026-08-26T08:00:00Z",
            )


if __name__ == "__main__":
    unittest.main()
