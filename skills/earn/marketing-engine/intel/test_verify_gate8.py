import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from verify_gate8 import Gate8Error, validate_enrichments, verify_gate8


INTEL = Path(__file__).resolve().parent
ENGINE = INTEL.parent


class Gate8VerifierTest(unittest.TestCase):
    def test_live_gate8_evidence_passes(self):
        result = verify_gate8(ENGINE)
        self.assertTrue(result["passed"])
        pipeline = result["source_pipeline"]
        self.assertGreaterEqual(pipeline["source_items"], 75)
        self.assertEqual(pipeline["judged_items"], pipeline["source_items"])
        self.assertEqual(pipeline["pending_items"], 0)
        self.assertGreaterEqual(pipeline["enrichments"], 11)
        counts = result["canonical_stores"]["counts"]
        self.assertGreaterEqual(counts["playbook"], 12)
        self.assertGreaterEqual(counts["hook-library"], 0)
        self.assertGreaterEqual(counts["creators"], 4)
        self.assertGreaterEqual(counts["ad-swipe"], 1)
        self.assertEqual(result["telegram"]["weekly_message_ids"], [5094])
        self.assertEqual(result["telegram"]["daily_message_ids"], [5095])
        self.assertTrue(result["idempotency"]["hashes_match"])

    def test_enrichment_rejects_wrong_evidence_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence = root / "capture.json"
            evidence.write_text("{}\n", encoding="utf-8")
            row = {
                "schema_version": "marketing.source-enrichment.v1",
                "id": "enrichment.fixture.x-1.v1",
                "tactic_id": "tactic.fixture.v1",
                "source_id": "x.fixture-articles",
                "item_id": "x:1",
                "source_url": "https://x.com/fixture/status/1",
                "captured_at": "2026-08-01T00:00:00Z",
                "evidence_path": str(evidence),
                "evidence_sha256": hashlib.sha256(b"different").hexdigest(),
            }
            store = root / "source-enrichments.jsonl"
            store.write_text(json.dumps(row) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(Gate8Error, "hash"):
                validate_enrichments(store)


if __name__ == "__main__":
    unittest.main(verbosity=2)
