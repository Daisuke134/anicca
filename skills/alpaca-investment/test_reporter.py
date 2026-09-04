import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import reporter


OBSERVATION = {
    "clock": {"observed_at": "2026-09-04T10:10:25Z"},
    "account": {
        "account_id": "must-not-appear",
        "equity": "99996.76",
        "cash": "99996.76",
    },
    "positions": [],
}
CAMPAIGN = {"realized_pnl_usd": "-3.00", "unrealized_pnl_usd": "0.00"}


class FailureBalanceTest(unittest.TestCase):
    def test_failure_report_reads_last_snapshot_and_names_it_as_latest(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            (state / "observation-latest.json").write_text(json.dumps(OBSERVATION))
            (state / "campaign.json").write_text(json.dumps(CAMPAIGN))
            with patch.object(
                reporter,
                "_deliver_message",
                return_value={"message_id": "123", "status": "delivered"},
            ) as send:
                reporter.deliver_failure(
                    state,
                    stage="observe",
                    effect_uncertain=False,
                    wake_id="2026-09-04T10:15:00Z",
                )

        message = send.call_args.args[2]
        self.assertIn("利用可能な最新値", message)
        self.assertIn("資産は $99,996.76", message)
        self.assertIn("現金は $99,996.76", message)
        self.assertIn("開始時$100,000から -$3.24", message)
        self.assertIn("確定損益 -$3.00", message)
        self.assertIn("含み損益 $0.00", message)
        self.assertIn("保有ポジション 0件", message)
        self.assertIn("2026-09-04T10:10:25Z", message)
        self.assertNotIn("must-not-appear", message)


if __name__ == "__main__":
    unittest.main()
