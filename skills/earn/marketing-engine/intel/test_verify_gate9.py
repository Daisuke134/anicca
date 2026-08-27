import unittest
from pathlib import Path

from verify_gate9 import verify_gate9


ENGINE = Path(__file__).resolve().parent.parent


class Gate9VerifierTest(unittest.TestCase):
    def test_live_gate9_evidence_passes(self):
        result = verify_gate9(ENGINE)
        self.assertTrue(result["passed"])
        counts = result["counts"]
        self.assertGreaterEqual(counts["video_observations"], 40)
        self.assertGreaterEqual(counts["video_transcripts"], 4)
        self.assertEqual(counts["video_judgments"], counts["video_transcripts"])
        self.assertGreaterEqual(counts["hooks"], 11)
        self.assertEqual(counts["hook_evidence"], counts["hooks"])
        self.assertGreaterEqual(result["hooks_by_language"]["en"], 5)
        self.assertGreaterEqual(result["hooks_by_language"]["ja"], 6)
        self.assertEqual(result["idempotency"]["new_observations"], 0)
        self.assertEqual(result["scheduled_run"]["telegram_message_ids"], [5102])
        self.assertEqual(result["scheduled_run"]["mine_command"][-2:], ["intel", "daily"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
