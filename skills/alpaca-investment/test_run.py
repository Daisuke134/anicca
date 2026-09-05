import json
import importlib.util
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import reporter as REPORTER
SPEC = importlib.util.spec_from_file_location("alpaca_investment_run", ROOT / "run.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _publisher_probe(root: Path) -> tuple[Path, Path]:
    marker = root / "publisher-called"
    executable = root / "node"
    executable.write_text('#!/bin/sh\n: > "$ALPACA_MARKER"\n', encoding="utf-8")
    executable.chmod(0o700)
    return executable, marker


class DeploymentProfileTest(unittest.TestCase):
    def test_accepts_only_exact_local_or_cloud(self):
        for value in ("local", "cloud"):
            with patch.dict(MODULE.os.environ, {
                "LIFE_MANAGER_INVESTMENT_DEPLOYMENT": value,
            }):
                self.assertEqual(MODULE._deployment(), value)

    def test_rejects_missing_or_non_exact_values(self):
        invalid_values = (None, "", "local,cloud", " local", "LOCAL")
        for value in invalid_values:
            environment = {} if value is None else {
                "LIFE_MANAGER_INVESTMENT_DEPLOYMENT": value,
            }
            with self.subTest(value=value), patch.dict(
                MODULE.os.environ, environment, clear=True
            ):
                with self.assertRaisesRegex(
                    ValueError, "^investment_deployment_invalid$"
                ):
                    MODULE._deployment()


class PortablePassTest(unittest.TestCase):
    @patch.object(MODULE, "reconcile_started", return_value={"pending": 0, "reconciled": 0})
    @patch.object(MODULE, "observe")
    @patch.object(MODULE, "read_campaign_snapshot", return_value={})
    @patch.object(MODULE, "reconcile")
    @patch.object(MODULE, "read_allocator_snapshot", return_value={})
    @patch.object(MODULE, "build_candidates", return_value=[])
    @patch.object(MODULE, "choose")
    @patch.object(MODULE, "deliver", return_value={"message_id": "123"})
    def test_success_has_no_dashboard_effect_or_public_summary(
        self, _deliver, choose, _build, _allocator, reconcile,
        _campaign, observe, _reconcile_started,
    ):
        observe.return_value = {
            "account": {"cash": "100000", "equity": "100000"},
            "activities_count": 0, "clock": {"observed_at": "2026-09-05T00:00:00Z"},
            "open_and_closed_orders_count": 0, "positions": [],
        }
        reconcile.return_value = {"exit_status": "CLOSED", "unrealized_pnl_usd": "0"}
        choose.return_value = {
            "approved": False, "candidate_ref": "NO_TRADE", "gate": "model_no_trade",
            "observed_at": "2026-09-05T00:00:00Z",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable, marker = _publisher_probe(root)
            with patch.dict(MODULE.os.environ, {
                "ALPACA_INVESTMENT_STATE_DIR": str(root / "state"),
                "NODE_BIN": str(executable), "ALPACA_MARKER": str(marker),
                "LIFE_MANAGER_INVESTMENT_DEPLOYMENT": "local",
            }), redirect_stdout(StringIO()) as output:
                self.assertEqual(MODULE.main(wake_id="wake-success"), 0)
            self.assertFalse(marker.exists())
            summary = json.loads(output.getvalue())
            self.assertNotIn("public_snapshot_published", summary)
            self.assertEqual(summary["deployment"], "local")
            receipts = [
                json.loads(line)
                for line in (root / "state" / "receipts.jsonl").read_text(
                    encoding="utf-8"
                ).splitlines()
            ]
            decision_receipt = next(
                receipt for receipt in receipts
                if receipt["receipt_type"] == "decision"
            )
            self.assertEqual(decision_receipt["decision"]["deployment"], "local")

    @patch.object(MODULE, "reconcile_started", return_value={"pending": 0, "reconciled": 0})
    @patch.object(MODULE, "observe", side_effect=RuntimeError("provider unavailable"))
    @patch.object(MODULE, "deliver_failure", return_value={"message_id": "123", "status": "delivered"})
    def test_terminal_failure_has_no_dashboard_effect(self, _deliver, _observe, _reconcile):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable, marker = _publisher_probe(root)
            with patch.dict(MODULE.os.environ, {
                "ALPACA_INVESTMENT_STATE_DIR": str(root / "state"),
                "NODE_BIN": str(executable), "ALPACA_MARKER": str(marker),
                "LIFE_MANAGER_INVESTMENT_DEPLOYMENT": "local",
            }), redirect_stdout(StringIO()):
                self.assertEqual(MODULE.main(wake_id="wake-failure"), 78)
            self.assertFalse(marker.exists())


class FailureTelegramTest(unittest.TestCase):
    @patch.object(MODULE, "deliver_failure", create=True)
    @patch.object(MODULE, "observe", side_effect=RuntimeError("provider payload must stay private"))
    @patch.object(MODULE, "reconcile_started", return_value={"pending": 0, "reconciled": 0})
    def test_terminal_failure_reports_once_after_internal_retries(
        self, _reconcile, observe, deliver_failure
    ):
        deliver_failure.return_value = {"message_id": "123", "status": "delivered"}
        with patch.dict(MODULE.os.environ, {
            "LIFE_MANAGER_INVESTMENT_DEPLOYMENT": "local",
        }):
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
