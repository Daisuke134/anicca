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
import alpaca_cli as CLI
import effect_store as EFFECT_STORE
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


class InvestmentModeTest(unittest.TestCase):
    def test_requires_exact_mode_before_broker_access(self):
        for value in ("paper", "shadow", "live", None, "", " paper", "PAPER", "paper,live"):
            with self.subTest(value=value):
                if value in {"paper", "shadow", "live"}:
                    with patch.dict(MODULE.os.environ, {"LIFE_MANAGER_INVESTMENT_MODE": value}):
                        self.assertEqual(MODULE._mode(), value)
                    continue
                with patch.dict(MODULE.os.environ, {
                    "LIFE_MANAGER_INVESTMENT_DEPLOYMENT": "local",
                    **({} if value is None else {"LIFE_MANAGER_INVESTMENT_MODE": value}),
                }, clear=True), patch.object(MODULE, "reconcile_started", return_value={"pending": 0, "reconciled": 0}), \
                        patch.object(MODULE, "observe", side_effect=RuntimeError("broker-called")) as observe, \
                        patch.object(MODULE, "deliver_failure", return_value={"status": "delivered"}):
                    MODULE.main(wake_id="mode-validation")
                self.assertEqual(observe.call_count, 0)

    def test_paper_mode_selects_configured_paper_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            credentials, state = root / "paper.json", root / "paper-state"
            observed = []
            def broker_boundary(**kwargs):
                observed.append(kwargs)
                raise RuntimeError("stop-at-broker-boundary")
            with patch.dict(MODULE.os.environ, {
                "LIFE_MANAGER_INVESTMENT_DEPLOYMENT": "local",
                "LIFE_MANAGER_INVESTMENT_MODE": "paper",
                "ALPACA_INVESTMENT_PAPER_CREDENTIALS_FILE": str(credentials),
                "ALPACA_INVESTMENT_PAPER_STATE_DIR": str(state),
            }, clear=True), patch.object(MODULE, "reconcile_started", return_value={"pending": 0, "reconciled": 0}) as reconcile, \
                    patch.object(MODULE, "observe", side_effect=broker_boundary), \
                    patch.object(MODULE, "deliver_failure", return_value={"status": "delivered"}):
                MODULE.main(wake_id="paper-paths")
        self.assertEqual(observed[0]["credentials_path"], credentials)
        self.assertEqual(reconcile.call_args.args[0], state / "receipts.jsonl")

    def test_receipts_and_reconciled_rows_expose_top_level_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "receipts.jsonl"
            EFFECT_STORE.record_no_trade(ledger, {"mode": "shadow", "candidate_ref": "NO_TRADE"})
            sealed = EFFECT_STORE.seal(ledger, {"mode": "paper", "candidate_ref": "TRADE"}, {"asset_class": "crypto"})
            EFFECT_STORE.mark_started(ledger, sealed)
            EFFECT_STORE.reconcile_started(ledger, lambda _: {"found": True, "status": "filled"})
            rows = [json.loads(line) for line in ledger.read_text().splitlines()]
        self.assertTrue(all(row.get("mode") in {"paper", "shadow"} for row in rows))


class BrokerContextTest(unittest.TestCase):
    def _credential(self, root, row):
        private = root / "private"
        private.mkdir(parents=True, mode=0o700)
        path = private / "credentials.json"
        path.write_text(json.dumps({"credentials": [row]}))
        path.chmod(0o600)
        return path

    def test_paper_and_live_contexts_use_separate_records(self):
        with tempfile.TemporaryDirectory() as directory:
            root, cli = Path(directory), Path(directory) / "alpaca"
            cli.write_text("#!/bin/sh\n[ \"$1\" = version ] && echo 0.0.14\n")
            cli.chmod(0o700)
            paper = self._credential(root / "paper", {
                "service": "app.alpaca.markets", "paper_endpoint": CLI.PAPER_ENDPOINT,
                "api_key": "paper-key", "api_secret": "paper-secret"})
            live = self._credential(root / "live", {
                "service": "app.alpaca.markets", "live_endpoint": "https://api.alpaca.markets/v2",
                "live_api_key": "live-key", "live_api_secret": "live-secret"})
            for mode, path, key, live_trade in (
                ("paper", paper, "paper-key", "false"),
                ("shadow", live, "live-key", "true"), ("live", live, "live-key", "true")):
                context = CLI._context(path, cli, mode=mode)
                self.assertEqual((context["ALPACA_API_KEY"], context["ALPACA_LIVE_TRADE"]),
                                 (key, live_trade))
            with self.assertRaises(ValueError):
                CLI._context(paper, cli, mode="live")


class ShadowReadOnlyTest(unittest.TestCase):
    def test_shadow_never_submits_campaign_exit_or_allocator_order(self):
        observation = {"account": {"cash": "100000", "equity": "100000"},
                       "activities_count": 0, "clock": {"observed_at": "2026-09-05T00:00:00Z"},
                       "open_and_closed_orders_count": 0, "positions": []}
        with tempfile.TemporaryDirectory() as directory, patch.dict(MODULE.os.environ, {
            "LIFE_MANAGER_INVESTMENT_MODE": "shadow", "LIFE_MANAGER_INVESTMENT_DEPLOYMENT": "local",
            "ALPACA_INVESTMENT_SHADOW_CREDENTIALS_FILE": str(Path(directory) / "live.json"),
            "ALPACA_INVESTMENT_SHADOW_STATE_DIR": str(Path(directory) / "shadow-state"),
        }, clear=True), patch.object(MODULE, "reconcile_started", return_value={"pending": 0, "reconciled": 0}), \
                patch.object(MODULE, "observe", return_value=observation), patch.object(MODULE, "read_campaign_snapshot"), \
                patch.object(MODULE, "reconcile", return_value={"exit_status": "EXIT_READY", "exit_credit_usd": "0.50", "unrealized_pnl_usd": "0.00"}), \
                patch.object(MODULE, "exit_order", return_value={"asset_class": "option_spread_close"}), \
                patch.object(MODULE, "read_allocator_snapshot", return_value={}), patch.object(MODULE, "build_candidates", return_value=[]), \
                patch.object(MODULE, "choose", return_value={"approved": True, "candidate_ref": "crypto://BTC/USD", "candidate": {"asset_class": "crypto"}, "gate": "approved", "observed_at": "2026-09-05T00:00:00Z"}), \
                patch.object(MODULE, "order_for", return_value={"asset_class": "crypto"}), patch.object(MODULE, "submit_order") as submit, \
                patch.object(MODULE, "deliver", return_value={"message_id": "123"}):
            self.assertEqual(MODULE.main(wake_id="shadow-read-only"), 0)
        submit.assert_not_called()


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
                "LIFE_MANAGER_INVESTMENT_MODE": "paper",
            }), redirect_stdout(StringIO()) as output:
                self.assertEqual(MODULE.main(wake_id="wake-success"), 0)
            self.assertFalse(marker.exists())
            summary = json.loads(output.getvalue())
            self.assertNotIn("public_snapshot_published", summary)
            self.assertEqual(summary["deployment"], "local")
            self.assertEqual(summary["mode"], "paper")
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
                "LIFE_MANAGER_INVESTMENT_MODE": "paper",
            }), redirect_stdout(StringIO()) as output:
                self.assertEqual(MODULE.main(wake_id="wake-failure"), 78)
            self.assertFalse(marker.exists())
            self.assertEqual(json.loads(output.getvalue())["mode"], "paper")


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
            "LIFE_MANAGER_INVESTMENT_MODE": "paper",
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
