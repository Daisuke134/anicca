import importlib.util
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock


class IntelDailyTest(unittest.TestCase):
    def test_lm_daily_runs_text_discovery_ingest_and_judge_in_order(self):
        lm_path = Path(__file__).resolve().parent.parent / "bin" / "lm"
        spec = importlib.util.spec_from_loader("marketing_lm_daily",
                                               SourceFileLoader("marketing_lm_daily", str(lm_path)))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp, \
                mock.patch.object(module.intel_daily, "run_daily") as daily:
            root = Path(temp)
            daily.return_value = {"status": "partial", "run_id": "fixture", "steps": {}}
            rc = module.main(["intel", "daily", "--intel-root", str(root / "intel"),
                              "--evidence-root", str(root / "evidence")])
            self.assertEqual(rc, 0)
            daily.assert_called_once()

    def test_hard_step_failure_makes_daily_failed_but_preserves_step_receipts(self):
        import intel_daily
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = intel_daily.run_daily(
                source_registry=root / "sources.json",
                video_registry=root / "video.json",
                intel_root=root / "intel", evidence_root=root / "evidence",
                pull=lambda **kwargs: {"status": "partial", "run_id": "pull"},
                discover=lambda **kwargs: {"status": "failed", "run_id": "discover"},
                ingest=lambda **kwargs: {"status": "skipped", "run_id": "ingest"},
                judge=lambda **kwargs: {"status": "skipped", "run_id": "judge"},
                run_id="daily-fixture", observed_at="2026-08-01T15:30:00Z")
            self.assertEqual(result["status"], "failed")
            self.assertEqual(list(result["steps"]), ["text_pull", "video_discover",
                                                     "video_ingest", "video_judge"])
            self.assertTrue((root / "evidence" / "daily-fixture" / "run.json").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
