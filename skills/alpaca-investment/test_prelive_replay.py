"""LP06: one sealed pre-live trajectory across every remaining safety boundary."""

from __future__ import annotations

import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO))

import alpaca_cli
import effect_store
import reporter
import risk_policy


class _TelegramClient:
    def __init__(self, sends: list[str]):
        self.sends = sends

    def send_text(self, message: str, *, chat_id: str):
        self.sends.append(message)
        return {"message_ids": ["prelive-message-1"]}


class PreliveReplayTest(unittest.TestCase):
    def test_sealed_trajectory_reconciles_once_and_never_reaches_shadow_broker(self):
        fixture = json.loads(
            (ROOT / "fixtures/prelive-replay.json").read_text(encoding="utf-8")
        )
        self.assertNotIn("credential", json.dumps(fixture).lower())

        rejected = fixture["risk_rejection"]
        risk = risk_policy.evaluate_entry(
            rejected["snapshot"], rejected["max_loss_usd"],
            now=risk_policy.parse_instant(rejected["now"]),
        )
        self.assertFalse(risk["approved"])
        self.assertEqual(risk["gate"], "fixed_risk_rejected")

        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            ledger = state / "receipts.jsonl"
            no_trade_id = effect_store.record_no_trade(ledger, fixture["no_trade"])
            self.assertEqual(
                no_trade_id, effect_store.record_no_trade(ledger, fixture["no_trade"])
            )

            sealed = effect_store.seal(
                ledger, fixture["paper_proposal"], fixture["paper_order"]
            )
            effect_store.mark_started(ledger, sealed)
            broker_reads: list[str] = []

            def missing_order(client_order_id: str):
                broker_reads.append(client_order_id)
                return None

            with self.assertRaisesRegex(ValueError, "^reconciliation_blocked$"):
                effect_store.reconcile_started(ledger, missing_order)

            restarted = importlib.reload(effect_store)

            def found_order(client_order_id: str):
                broker_reads.append(client_order_id)
                return {"client_order_id": client_order_id, "status": "filled"}

            recovered = restarted.reconcile_started(ledger, found_order)
            replayed = restarted.reconcile_started(
                ledger, lambda value: self.fail(f"duplicate broker read: {value}")
            )
            self.assertEqual(recovered, {"pending": 1, "reconciled": 1, "unresolved": 0})
            self.assertEqual(replayed, {"pending": 0, "reconciled": 0, "unresolved": 0})
            self.assertEqual(broker_reads, [sealed["client_order_id"]] * 2)

            sends: list[str] = []
            with patch.object(
                reporter, "_telegram_client",
                return_value=(_TelegramClient(sends), "fixture-chat"),
            ):
                delivered = reporter.deliver(
                    state, fixture["observation"], fixture["campaign"],
                    fixture["no_trade"], "none",
                )
                duplicate = reporter.deliver(
                    state, fixture["observation"], fixture["campaign"],
                    fixture["no_trade"], "none",
                )
            self.assertEqual(delivered["message_id"], duplicate["message_id"])
            self.assertEqual(delivered["status"], duplicate["status"])
            self.assertEqual(len(sends), 1)

            with patch.object(alpaca_cli, "_context") as context, patch.object(
                alpaca_cli, "_run"
            ) as broker:
                shadow = fixture["shadow_proposal"]
                self.assertTrue(shadow["approved"])
                with self.assertRaisesRegex(
                    ValueError, "^investment_mode_effect_forbidden$"
                ):
                    alpaca_cli.submit_order(
                        credentials_path=Path("unused"), cli_path=Path("unused"),
                        client_order_id=sealed["client_order_id"],
                        order=fixture["paper_order"], mode=shadow["mode"],
                    )
            context.assert_not_called()
            broker.assert_not_called()

            rows = [json.loads(line) for line in ledger.read_text().splitlines()]
            self.assertEqual(sum(row.get("outcome") == "no_trade" for row in rows), 1)
            self.assertEqual(sum(row.get("receipt_type") == "outcome" for row in rows), 1)
            self.assertEqual(restarted.unresolved_intent_count(ledger), 0)


if __name__ == "__main__":
    unittest.main()
