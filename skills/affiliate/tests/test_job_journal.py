import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from job_journal import JobStateError, reconcile_effect, resume_effect, start_effect, verify_effect


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
            resumed = resume_effect(state, "X_POST", "placement-1")
            self.assertEqual(resumed["state"], "EFFECT_STARTED")
            self.assertEqual(resumed["run_id"], job["run_id"])
            self.assertEqual(resumed["job_id"], job["job_id"])
            self.assertEqual(resumed["attempt"], 2)
            done = reconcile_effect(state, "X_POST", "placement-1", {"state": "LIVE", "public_id": "123"})
            self.assertEqual(done["state"], "VERIFIED")
            self.assertEqual(done["run_id"], job["run_id"])
            self.assertEqual(done["job_id"], job["job_id"])
            self.assertEqual(done["attempt"], 3)
            self.assertTrue(done["resumed"])
            self.assertEqual(len((state / "job-events.jsonl").read_text().splitlines()), 3)
            self.assertEqual((state / "job-events.jsonl").stat().st_mode & 0o077, 0)


if __name__ == "__main__":
    unittest.main()
