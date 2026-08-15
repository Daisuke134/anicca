import importlib.util
import sys
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
