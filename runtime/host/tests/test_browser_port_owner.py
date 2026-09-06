import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "browser_port_owner.py"
LANCERS_LAUNCHER = Path(__file__).parents[3] / "runtime/legacy/lancers-revenue-browser/run.sh"


class BrowserPortOwnerTests(unittest.TestCase):
    def test_lancers_launcher_reexecutes_through_shared_owner(self):
        launcher = LANCERS_LAUNCHER.read_text(encoding="utf-8")
        self.assertIn('runtime/host/browser_port_owner.py', launcher)
        self.assertIn('--owner lancers-revenue-browser', launcher)
        self.assertIn('LANCERS_BROWSER_PORT_OWNED=1', launcher)

    def test_second_owner_for_same_port_fails_closed_while_first_is_alive(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state"
            first = subprocess.Popen(
                [sys.executable, str(SCRIPT), "run", "--state-dir", str(state),
                 "--port", "9222", "--profile", "/profiles/daily", "--owner", "daily",
                 "--", sys.executable, "-c", "import time; time.sleep(10)"],
            )
            try:
                deadline = time.monotonic() + 3
                receipt = state / "9222.json"
                while not receipt.exists() and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue(receipt.exists())
                second = subprocess.run(
                    [sys.executable, str(SCRIPT), "run", "--state-dir", str(state),
                     "--port", "9222", "--profile", "/profiles/job-search", "--owner", "job-search",
                     "--", sys.executable, "-c", "raise SystemExit(0)"],
                    capture_output=True, text=True, check=False,
                )
                self.assertEqual(second.returncode, 75)
                conflict = json.loads(second.stderr)
                self.assertEqual(conflict["reason"], "browser_port_owned")
                self.assertEqual(conflict["port"], 9222)
                self.assertEqual(conflict["current_owner"], "daily")
                self.assertNotIn("profile", conflict)
            finally:
                first.terminate()
                first.wait(timeout=3)

    def test_different_ports_can_run_concurrently(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state"
            first = subprocess.Popen(
                [sys.executable, str(SCRIPT), "run", "--state-dir", str(state),
                 "--port", "9222", "--profile", "/profiles/daily", "--owner", "daily",
                 "--", sys.executable, "-c", "import time; time.sleep(10)"],
            )
            try:
                time.sleep(0.1)
                second = subprocess.run(
                    [sys.executable, str(SCRIPT), "run", "--state-dir", str(state),
                     "--port", "9223", "--profile", "/profiles/gig", "--owner", "gig",
                     "--", sys.executable, "-c", "raise SystemExit(0)"],
                    capture_output=True, text=True, check=False,
                )
                self.assertEqual(second.returncode, 0, second.stderr)
            finally:
                first.terminate()
                first.wait(timeout=3)


if __name__ == "__main__":
    unittest.main()
