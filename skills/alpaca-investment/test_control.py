import json
import os
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from control import apply_control, read_control
import run as investment_run
import reporter


@contextmanager
def _paused_fence(_root):
    yield {"paused": True, "killed": False, "revision": 1}


class _TelegramClient:
    def __init__(self, sends):
        self.sends = sends

    def send_text(self, message, *, chat_id):
        self.sends.append((message, chat_id))
        return {"message_ids": ["control-message"]}


class ControlStateTest(unittest.TestCase):
    def test_control_transitions_are_durable_idempotent_and_kill_is_terminal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertTrue(apply_control(root, "pause", "2026-09-07T00:00:00Z")["changed"])
            self.assertFalse(apply_control(root, "pause", "2026-09-07T00:00:01Z")["changed"])
            self.assertTrue(apply_control(root, "resume", "2026-09-07T00:00:02Z")["changed"])
            self.assertTrue(apply_control(root, "kill", "2026-09-07T00:00:03Z")["changed"])
            self.assertFalse(apply_control(root, "resume", "2026-09-07T00:00:04Z")["changed"])
            self.assertEqual(read_control(root / "control.json")["revision"], 3)

    def test_missing_state_runs_and_pause_or_kill_survives_reread(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "control.json"
            self.assertEqual(read_control(path), {"paused": False, "killed": False})
            for value in (
                {"paused": True, "killed": False, "revision": 1, "last_action": "pause"},
                {"paused": True, "killed": True, "revision": 2, "last_action": "kill"},
            ):
                path.write_text(json.dumps(value), encoding="utf-8")
                self.assertEqual(read_control(path), value)

    def test_unknown_or_inconsistent_state_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "control.json"
            for raw in (
                "null", "{}", '{"paused":false,"killed":true}',
                '{"paused":true,"killed":false,"revision":1,"capital":1000}',
            ):
                path.write_text(raw, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "^investment_control_state_invalid$"):
                    read_control(path)

    def test_paused_wake_reconciles_then_makes_zero_market_or_broker_effect_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            (state / "control.json").write_text(
                '{"paused":true,"killed":false,"revision":1,"last_action":"pause"}', encoding="utf-8")
            env = {
                "LIFE_MANAGER_INVESTMENT_MODE": "paper",
                "LIFE_MANAGER_INVESTMENT_DEPLOYMENT": "local",
                "ALPACA_INVESTMENT_STATE_DIR": directory,
            }
            with patch.dict(os.environ, env, clear=True), \
                    patch.object(investment_run, "reconcile_started", return_value={
                        "pending": 0, "reconciled": 0, "unresolved": 0}) as reconcile, \
                    patch.object(investment_run, "observe") as observe, \
                    patch.object(investment_run, "read_allocator_snapshot") as allocator, \
                    patch.object(investment_run, "submit_order") as submit, \
                    patch.object(investment_run, "deliver_control", return_value={
                        "message_id": "fixture"}) as deliver:
                self.assertEqual(investment_run.main(wake_id="fixture-wake"), 0)
            reconcile.assert_called_once()
            observe.assert_not_called()
            allocator.assert_not_called()
            submit.assert_not_called()
            deliver.assert_called_once()

    def test_pause_accepted_during_decision_fences_submit(self):
        observation = {
            "account": {"cash": "100000", "equity": "100000"},
            "activities_count": 0,
            "clock": {"observed_at": "2026-09-07T00:00:00Z"},
            "open_and_closed_orders_count": 0,
            "positions": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            env = {
                "LIFE_MANAGER_INVESTMENT_MODE": "paper",
                "LIFE_MANAGER_INVESTMENT_DEPLOYMENT": "local",
                "ALPACA_INVESTMENT_STATE_DIR": directory,
            }
            with patch.dict(os.environ, env, clear=True), \
                    patch.object(investment_run, "reconcile_started", return_value={
                        "pending": 0, "reconciled": 0, "unresolved": 0}), \
                    patch.object(investment_run, "read_control", return_value={
                        "paused": False, "killed": False}), \
                    patch.object(investment_run, "observe", return_value=observation), \
                    patch.object(investment_run, "read_campaign_snapshot", return_value={}), \
                    patch.object(investment_run, "reconcile", return_value={
                        "exit_status": "CLOSED", "unrealized_pnl_usd": "0"}), \
                    patch.object(investment_run, "read_allocator_snapshot", return_value={
                        "risk": {}, "unresolved_intents": 0}), \
                    patch.object(investment_run, "build_candidates", return_value=[]), \
                    patch.object(investment_run, "choose", return_value={
                        "approved": True, "candidate_ref": "crypto://BTC/USD",
                        "candidate": {"asset_class": "crypto"}, "gate": "approved"}), \
                    patch.object(investment_run, "order_for", return_value={
                        "asset_class": "crypto"}), \
                    patch.object(investment_run, "control_fence", _paused_fence), \
                    patch.object(investment_run, "submit_order") as submit, \
                    patch.object(investment_run, "deliver_control", return_value={
                        "message_id": "paused-at-fence"}) as deliver:
                self.assertEqual(investment_run.main(wake_id="pause-race"), 0)
            submit.assert_not_called()
            deliver.assert_called_once()
            self.assertFalse((Path(directory) / "receipts.jsonl").exists())

    def test_same_control_wake_sends_one_provider_message(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            sends = []
            with patch.object(reporter, "_telegram_client", return_value=(
                    _TelegramClient(sends), "owner")):
                first = reporter.deliver_control(
                    state, control={"paused": True, "killed": False},
                    wake_id="same-wake", mode="paper")
                second = reporter.deliver_control(
                    state, control={"paused": True, "killed": False},
                    wake_id="same-wake", mode="paper")
            self.assertEqual(first["message_id"], second["message_id"])
            self.assertEqual(first["status"], second["status"])
            self.assertEqual(len(sends), 1)


if __name__ == "__main__":
    unittest.main()
