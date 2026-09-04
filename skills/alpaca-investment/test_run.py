import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import reporter as REPORTER
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
    @patch.object(MODULE, "reconcile_started", return_value={"pending": 0, "reconciled": 0})
    @patch.object(MODULE, "observe", side_effect=RuntimeError("provider payload must stay private"))
    @patch.object(MODULE, "deliver_failure")
    @patch.object(MODULE, "_publish_public_snapshot", return_value=False)
    def test_final_failure_publishes_after_telegram_delivery_and_stays_blocked(
        self, publish_snapshot, deliver_failure, _observe, _reconcile
    ):
        events = []

        def record_failure_delivery(*_args, **_kwargs):
            events.append("telegram")
            return {"message_id": "123", "status": "delivered"}

        def record_snapshot_publication(*_args, **_kwargs):
            events.append("snapshot")
            raise RuntimeError("public sink unavailable")

        deliver_failure.side_effect = record_failure_delivery
        publish_snapshot.side_effect = record_snapshot_publication

        self.assertEqual(MODULE.main(), 78)
        self.assertEqual(events, ["telegram", "snapshot"])
        publish_snapshot.assert_called_once_with()

    @patch.object(MODULE, "reconcile_started", return_value={"pending": 0, "reconciled": 0})
    @patch.object(MODULE, "observe", side_effect=RuntimeError("provider payload must stay private"))
    @patch.object(MODULE, "deliver_failure", side_effect=RuntimeError("telegram store unavailable"))
    @patch.object(MODULE, "_publish_public_snapshot")
    def test_failure_delivery_exception_skips_publication_and_stays_blocked(
        self, publish_snapshot, _deliver_failure, _observe, _reconcile
    ):
        self.assertEqual(MODULE.main(), 78)
        publish_snapshot.assert_not_called()

    @patch.object(MODULE, "deliver_failure", create=True)
    @patch.object(MODULE, "observe", side_effect=RuntimeError("provider payload must stay private"))
    @patch.object(MODULE, "reconcile_started", return_value={"pending": 0, "reconciled": 0})
    def test_terminal_failure_reports_once_after_internal_retries(
        self, _reconcile, observe, deliver_failure
    ):
        deliver_failure.return_value = {"message_id": "123", "status": "delivered"}
        self.assertEqual(MODULE.main(), 78)
        self.assertEqual(observe.call_count, 3)
        deliver_failure.assert_called_once()
        self.assertEqual(deliver_failure.call_args.kwargs["stage"], "observe")
        self.assertFalse(deliver_failure.call_args.kwargs["effect_uncertain"])
        self.assertNotIn("provider payload", str(deliver_failure.call_args))

    def test_telegram_delivery_failure_is_not_retried(self):
        self.assertFalse(MODULE._retry_allowed("telegram_deliver", False, 0))
        self.assertTrue(MODULE._retry_allowed("observe", False, 0))

    def test_reconciliation_failure_does_not_claim_that_no_order_exists(self):
        message = REPORTER.render_failure(
            stage="reconcile_started", effect_uncertain=True,
            wake_id="2026-09-04T00:00:00Z",
        )
        self.assertIn("送信した可能性", message)
        self.assertNotIn("注文は実行していません", message)

    def test_terminal_effect_is_unknown_after_submit(self):
        self.assertEqual(MODULE._terminal_effect(False), "none")
        self.assertEqual(MODULE._terminal_effect(True), "unknown")


if __name__ == "__main__":
    unittest.main()
