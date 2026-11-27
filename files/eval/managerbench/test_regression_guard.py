import tempfile, unittest
from pathlib import Path
from regression_guard import evaluate, candidate_preflight

class RegressionGuardTests(unittest.TestCase):
    def test_unpinned_receipt_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"r.json";p.write_text("{}")
            with self.assertRaisesRegex(ValueError,"digest"):evaluate(p)
    def test_unknown_or_mismatched_candidate(self):
        report={"candidates":{"a":{"checkpoint_sha256":"a"*64,"status":"BLOCKED_REGRESSION"}}}
        self.assertEqual(candidate_preflight(report,"missing","a"*64),"BLOCKED_UNKNOWN_CANDIDATE")
        self.assertEqual(candidate_preflight(report,"a","b"*64),"BLOCKED_UNKNOWN_CANDIDATE")
        self.assertEqual(candidate_preflight(report,"a","a"*64),"BLOCKED_REGRESSION")
    def test_pass_not_release(self):
        report={"candidates":{"a":{"checkpoint_sha256":"a"*64,"status":"SCREEN_PASS_NOT_APPROVED"}}}
        self.assertEqual(candidate_preflight(report,"a","a"*64),"SCREEN_PASS_NOT_APPROVED")
