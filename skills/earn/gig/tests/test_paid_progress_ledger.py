import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "paid_progress_ledger.py"
SPEC = importlib.util.spec_from_file_location("paid_progress_ledger", SCRIPT)
assert SPEC and SPEC.loader
paid_progress = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = paid_progress
SPEC.loader.exec_module(paid_progress)


class PaidProgressLedgerTest(unittest.TestCase):
    def reconciled(self, *, send_performed):
        return {
            "ok": True,
            "request_id": "contract-42",
            "talkroom_id": "42",
            "buyer_visible": True,
            "send_performed": send_performed,
            "latest_buyer_visible_version": "v3",
            "latest_buyer_visible_package_sha256": "a" * 64,
        }

    def test_fresh_buyer_visible_send_is_recorded_once(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger = Path(temp) / "paid-progress.jsonl"
            first = paid_progress.record(
                self.reconciled(send_performed=True),
                pass_id="pass-1",
                evidence_dir="/evidence/pass-1",
                ledger=ledger,
            )
            repeated = paid_progress.record(
                self.reconciled(send_performed=True),
                pass_id="pass-1",
                evidence_dir="/evidence/pass-1",
                ledger=ledger,
            )
            self.assertTrue(first)
            self.assertFalse(repeated)
            rows = [json.loads(line) for line in ledger.read_text().splitlines()]
            self.assertEqual(len(rows), 1)

    def test_verified_observation_without_a_new_send_is_a_noop(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger = Path(temp) / "paid-progress.jsonl"
            recorded = paid_progress.record(
                self.reconciled(send_performed=False),
                pass_id="pass-observe",
                evidence_dir="/evidence/pass-observe",
                ledger=ledger,
            )
            self.assertFalse(recorded)
            self.assertFalse(ledger.exists())

    def test_fresh_buyer_visible_text_answer_is_recorded_without_new_artifact(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger = Path(temp) / "paid-progress.jsonl"
            reconciled = {
                "ok": True,
                "request_id": "contract-42",
                "talkroom_id": "42",
                "buyer_visible_response": True,
                "send_performed": True,
                "current_version": "v3",
                "current_package_sha256": "a" * 64,
            }
            self.assertTrue(paid_progress.record(
                reconciled,
                pass_id="answer-pass",
                evidence_dir="/evidence/answer-pass",
                ledger=ledger,
            ))
            row = json.loads(ledger.read_text())
            self.assertEqual(row["requestId"], "contract-42")
            self.assertEqual(row["artifact_version"], "v3")


if __name__ == "__main__":
    unittest.main()
