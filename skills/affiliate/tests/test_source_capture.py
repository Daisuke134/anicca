import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts" / "source_capture.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("affiliate_source_capture", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SourceCaptureTest(unittest.TestCase):
    def test_failure_classes_are_explicit(self):
        self.assertIsNone(MODULE.classify_failure(0, "body"))
        self.assertEqual(MODULE.classify_failure(0, ""), "EMPTY")
        self.assertEqual(MODULE.classify_failure(1, "HTTP 429"), "RATE_LIMIT")
        self.assertEqual(MODULE.classify_failure(1, "HTTP 403"), "AUTH")
        self.assertEqual(MODULE.classify_failure(1, "boom"), "UPSTREAM")

    def test_refresh_all_plans_writes_one_daily_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "skill"
            plans = root / "config" / "source-plans"
            plans.mkdir(parents=True)
            for plan_id in ("alpha-en", "beta-en"):
                (plans / f"{plan_id}.json").write_text(json.dumps({
                    "schema_version": 1, "plan_id": plan_id, "locale": "en", "sources": [],
                }))
            state = Path(directory) / "state"
            with mock.patch.object(MODULE, "capture", return_value=[]):
                receipt = MODULE.refresh_all(root, state, now=1000, cooldown_seconds=86400)
                replay = MODULE.refresh_all(root, state, now=1001, cooldown_seconds=86400)
            self.assertEqual(receipt["state"], "COMPLETE")
            self.assertEqual([row["plan_id"] for row in receipt["plans"]], ["alpha-en", "beta-en"])
            self.assertEqual(replay["state"], "COOLDOWN")


if __name__ == "__main__":
    unittest.main()
