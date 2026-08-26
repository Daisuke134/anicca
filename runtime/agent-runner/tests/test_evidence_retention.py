import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_runner import reclaim_completed_evidence


class EvidenceRetentionTest(unittest.TestCase):
    def completed_run(self, root: Path, task: str, name: str, payload: bytes) -> Path:
        run = root / task / name
        run.mkdir(parents=True)
        (run / "summary.json").write_text("{}", encoding="utf-8")
        (run / "attempt-01.stdout.log").write_bytes(payload)
        return run

    def test_evicts_oldest_completed_runs_but_preserves_current_and_active(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "state" / "agent-runner-evidence"
            old = self.completed_run(root, "capafy", "old", b"a" * 64)
            time.sleep(0.01)
            current = self.completed_run(root, "capafy", "current", b"b" * 64)
            active = root / "capafy" / "active"
            active.mkdir()
            (active / "runner.stdout.log").write_bytes(b"c" * 64)

            result = reclaim_completed_evidence(
                current, min_free_bytes=0, max_evidence_bytes=150,
            )

            self.assertEqual(result["reclaimed_runs"], 1)
            self.assertFalse(old.exists())
            self.assertTrue(current.exists())
            self.assertTrue(active.exists())

    def test_unmanaged_path_is_never_reclaimed(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "arbitrary" / "run"
            path.mkdir(parents=True)
            result = reclaim_completed_evidence(path, min_free_bytes=0, max_evidence_bytes=0)
            self.assertEqual(result, {"reclaimed_bytes": 0, "reclaimed_runs": 0})


if __name__ == "__main__":
    unittest.main()
