import unittest
from pathlib import Path


DAILY_LOOP = Path(__file__).resolve().parents[1] / "scripts" / "daily_loop.sh"
RUNBOOK = Path(__file__).resolve().parents[1] / "DAILY_LOOP.md"


class ProviderAgnosticRunnerTest(unittest.TestCase):
    def test_publish_drainer_uses_shared_runner_instead_of_direct_claude(self):
        text = DAILY_LOOP.read_text(encoding="utf-8")

        self.assertIn("run_agent.sh", text)
        self.assertIn("--task-class tool-agent", text)
        self.assertNotRegex(text, r"\bclaude\s+-p\b")

    def test_rejected_retry_reuses_its_slot_even_when_unlisted_cap_is_full(self):
        text = RUNBOOK.read_text(encoding="utf-8")

        self.assertRegex(
            text,
            r"A REVIEW_REJECTED retry\s+reuses its existing slot and MUST proceed even when unlisted is 5",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
