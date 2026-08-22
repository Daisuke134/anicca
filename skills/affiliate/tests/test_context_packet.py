from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SKILL_ROOT / "scripts" / "context_packet.py"


class ContextPacketTests(unittest.TestCase):
    def test_packet_is_allowlisted_and_contains_no_private_or_tracking_bytes(self) -> None:
        self.assertTrue(MODULE_PATH.is_file(), f"missing context builder: {MODULE_PATH}")
        spec = importlib.util.spec_from_file_location("context_packet", MODULE_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        packet = module.build(
            goal={
                "goal_id": "goal-1", "objective": "Reach verified USD 10K net",
                "success_gate": "ROLLING_30D_NET_10K", "password": "leak-password",
            },
            unfinished_job={
                "job_id": "job-1", "stage": "RECONCILE", "state": "PENDING",
                "placement_id": "placement-1", "customer_id": "private-customer",
            },
            due_times={"revenue": "2026-08-22T00:00:00Z", "unrelated": "private-state"},
            allowed_commands=["revenue reconcile", "x post publish"],
            receipts=[{
                "receipt_type": "AFFILIATE_ROLLING_NET", "state": "NO_TRANSACTIONS",
                "money_state": "NO_TRANSACTIONS", "transaction_count": 0,
                "tracking_link": "https://tracking.invalid/?ref=raw-secret",
                "provider_account_id": "private-provider", "clicks": 99, "views": 999,
            }],
        )
        encoded = json.dumps(packet, sort_keys=True)
        for forbidden in (
            "leak-password", "private-customer", "private-state", "raw-secret",
            "private-provider", "tracking.invalid", "clicks", "views", "unrelated",
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertEqual(packet["goal"]["goal_id"], "goal-1")
        self.assertEqual(packet["unfinished_job"]["placement_id"], "placement-1")
        self.assertEqual(packet["receipts"][0]["money_state"], "NO_TRANSACTIONS")
        self.assertEqual(
            [row["command"] for row in packet["allowed_tools"]],
            ["revenue reconcile", "x post publish"],
        )
        self.assertTrue(all("input_schema" in row for row in packet["allowed_tools"]))


if __name__ == "__main__":
    unittest.main()
