import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
WRAPPER = SKILL / "scripts" / "run_with_cdp_lock.sh"


class PaidDeliveryLockTest(unittest.TestCase):
    def env(
        self, lock_dir: Path, stale: str = "0", heartbeat: str = "30"
    ) -> dict[str, str]:
        env = os.environ.copy()
        env.update({
            "CDP_LOCK_DIR": str(lock_dir),
            "CDP_LOCK_STALE_SECS": stale,
            "CDP_LOCK_HEARTBEAT_SECS": heartbeat,
        })
        return env

    def test_long_running_holder_refreshes_lease_timestamp(self):
        with tempfile.TemporaryDirectory() as temp:
            lock = Path(temp) / ".cdp-gig.lock"
            child_code = (
                "from pathlib import Path; import time; "
                f"meta=Path({str(lock / 'meta')!r}); "
                "first=meta.stat().st_mtime_ns; time.sleep(2.2); "
                "assert meta.stat().st_mtime_ns > first"
            )
            result = subprocess.run(
                [
                    str(WRAPPER),
                    "gig-pass",
                    "0",
                    "--",
                    sys.executable,
                    "-c",
                    child_code,
                ],
                env=self.env(lock, "1500", "1"),
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(lock.exists())

    def test_lock_contention_defers_without_running_child_and_releases(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock = root / ".cdp-9222.lock"
            marker = root / "ran"
            lock.mkdir()
            (lock / "meta").write_text("auditor 999\n")
            result = subprocess.run(
                [str(WRAPPER), "paid-delivery", "0", "--", sys.executable, "-c", f"Path({str(marker)!r}).touch()"],
                env=self.env(lock, "1500"), text=True, capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(marker.exists())
            (lock / "meta").unlink()
            lock.rmdir()
            child_code = (
                "from pathlib import Path; import re; "
                f"value=Path({str(lock / 'meta')!r}).read_text(); "
                "assert re.fullmatch(r'paid-delivery \\d+\\n', value), value; "
                f"Path({str(marker)!r}).write_text(value)"
            )
            result = subprocess.run(
                [str(WRAPPER), "paid-delivery", "0", "--", sys.executable, "-c", child_code],
                env=self.env(lock), text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertRegex(marker.read_text(), r"^paid-delivery \d+\n$")
            self.assertFalse(lock.exists())

    def test_killed_wrapper_leaves_reclaimable_lock(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock = root / ".cdp-9222.lock"
            child = subprocess.Popen(
                [str(WRAPPER), "paid-delivery", "0", "--", sys.executable, "-c", "import time; time.sleep(30)"],
                env=self.env(lock), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            try:
                for _ in range(100):
                    if (lock / "meta").exists():
                        break
                    time.sleep(0.01)
                self.assertTrue((lock / "meta").exists())
                child.kill()
                child.wait(timeout=3)
                marker = root / "reclaimed"
                result = subprocess.run(
                    [str(WRAPPER), "paid-delivery", "0", "--", sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).touch()"],
                    env=self.env(lock), text=True, capture_output=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(marker.exists())
                self.assertFalse(lock.exists())
            finally:
                child.kill()
                child.wait(timeout=3)

    def test_partial_lock_creation_without_meta_is_reclaimable(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock = root / ".cdp-9222.lock"
            lock.mkdir()
            marker = root / "reclaimed"
            result = subprocess.run(
                [str(WRAPPER), "paid-delivery", "0", "--", sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).touch()"],
                env=self.env(lock), text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(marker.exists())
            self.assertFalse(lock.exists())


if __name__ == "__main__":
    unittest.main()
