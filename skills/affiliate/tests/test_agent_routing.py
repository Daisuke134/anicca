from __future__ import annotations

import json
import unittest
from pathlib import Path


CONFIG = Path(__file__).resolve().parents[1] / "config" / "agent-runner.json"


class AffiliateAgentRoutingTests(unittest.TestCase):
    def test_strategy_and_repair_routes_are_explicit_and_single_candidate(self) -> None:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        strategy = config["task_classes"]["marketing-agent"]
        repair = config["task_classes"]["escalation-agent"]

        self.assertEqual(strategy["route"], "affiliate-terra-high-strategy")
        self.assertTrue(strategy["requires_explicit_escalation"])
        self.assertEqual(
            strategy["candidates"],
            [{"provider": "codex", "model": "gpt-5.6-terra", "effort": "high"}],
        )
        self.assertEqual(repair["route"], "affiliate-sol-one-use-repair")
        self.assertTrue(repair["requires_explicit_escalation"])
        self.assertEqual(
            repair["candidates"],
            [{"provider": "codex", "model": "gpt-5.6-sol", "effort": "high"}],
        )


if __name__ == "__main__":
    unittest.main()
