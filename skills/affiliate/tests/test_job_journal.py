import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from job_journal import JobStateError, start_effect, verify_effect


class JobJournalTest(unittest.TestCase):
    def test_write_ahead_identity_reconcile_gate_and_verified_history(self):
        with tempfile.TemporaryDirectory() as root:
            state = Path(root)
            job = start_effect(state, "X_POST", "placement-1", {"content_sha256": "a" * 64},
                               {"state": "NOT_FOUND"}, 3600)
            self.assertEqual(job["state"], "EFFECT_STARTED")
            self.assertEqual(job["attempt"], 1)
            self.assertTrue(job["run_id"] and job["job_id"] and job["action_fingerprint"])
            with self.assertRaises(JobStateError):
                start_effect(state, "X_POST", "placement-1", {"content_sha256": "a" * 64},
                             {"state": "NOT_FOUND"}, 3600)
            done = verify_effect(state, job["job_id"], {"state": "LIVE", "public_id": "123"})
            self.assertEqual(done["state"], "VERIFIED")
            self.assertEqual(len((state / "job-events.jsonl").read_text().splitlines()), 2)
            self.assertEqual((state / "job-events.jsonl").stat().st_mode & 0o077, 0)


if __name__ == "__main__":
    unittest.main()
