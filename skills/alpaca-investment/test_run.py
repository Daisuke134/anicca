import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
SPEC = importlib.util.spec_from_file_location("alpaca_investment_run", ROOT / "run.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PublicSnapshotTest(unittest.TestCase):
    @patch.object(MODULE.subprocess, "run")
    def test_publication_is_one_bounded_best_effort_child(self, run):
        run.return_value.returncode = 0
        self.assertTrue(MODULE._publish_public_snapshot())
        run.assert_called_once()
        self.assertFalse(run.call_args.kwargs["check"])
        self.assertEqual(run.call_args.kwargs["timeout"], 20)

    @patch.object(MODULE.subprocess, "run", side_effect=subprocess.TimeoutExpired("node", 20))
    def test_publication_timeout_cannot_escape_into_pass_retry(self, _run):
        self.assertFalse(MODULE._publish_public_snapshot())


class FailureTelegramTest(unittest.TestCase):
    @patch.object(MODULE, "deliver_failure", create=True)
    @patch.object(MODULE, "observe", side_effect=OSError("provider payload must stay private"))
    @patch.object(MODULE, "reconcile_started", return_value={"pending": 0, "reconciled": 0})
    def test_terminal_failure_reports_once_after_internal_retries(
        self, _reconcile, observe, deliver_failure
    ):
        deliver_failure.return_value = {"message_id": "123", "status": "delivered"}
        self.assertEqual(MODULE.main(), 78)
        self.assertEqual(observe.call_count, 3)
        deliver_failure.assert_called_once()
        self.assertEqual(deliver_failure.call_args.kwargs["stage"], "observe")
        self.assertFalse(deliver_failure.call_args.kwargs["effect_attempted"])
        self.assertNotIn("provider payload", str(deliver_failure.call_args))


if __name__ == "__main__":
    unittest.main()
