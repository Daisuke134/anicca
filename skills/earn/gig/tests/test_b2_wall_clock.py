import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "b2_wall_clock.py"


class B2WallClockTest(unittest.TestCase):
    def plan(self, *, pass_start: int, now: int, output: Path) -> tuple[int, dict]:
        proc = subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "plan",
                "--pass-start",
                str(pass_start),
                "--now",
                str(now),
                "--wall-limit",
                "3480",
                "--finalize-reserve",
                "120",
                "--min-invocation",
                "600",
                "--output",
                str(output),
            ],
            text=True,
            capture_output=True,
        )
        payload = json.loads(output.read_text(encoding="utf-8"))
        return proc.returncode, payload

    def test_allows_a_bounded_continuation_when_ten_minutes_remain(self):
        with tempfile.TemporaryDirectory() as directory:
            rc, payload = self.plan(
                pass_start=1_000,
                now=3_700,
                output=Path(directory) / "plan.json",
            )
        self.assertEqual(rc, 0)
        self.assertTrue(payload["can_start"])
        self.assertEqual(payload["runner_timeout_seconds"], 660)
        self.assertEqual(payload["deadline_epoch"], 4_360)

    def test_yields_when_less_than_one_bounded_invocation_remains(self):
        with tempfile.TemporaryDirectory() as directory:
            rc, payload = self.plan(
                pass_start=1_000,
                now=3_800,
                output=Path(directory) / "plan.json",
            )
        self.assertEqual(rc, 3)
        self.assertFalse(payload["can_start"])
        self.assertEqual(payload["runner_timeout_seconds"], 0)
        self.assertEqual(payload["reason"], "next_hour_deadline")

    def test_rejects_a_configuration_without_finalize_reserve(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "plan.json"
            proc = subprocess.run(
                [
                    "python3",
                    str(SCRIPT),
                    "plan",
                    "--pass-start",
                    "1000",
                    "--now",
                    "1000",
                    "--wall-limit",
                    "600",
                    "--finalize-reserve",
                    "600",
                    "--min-invocation",
                    "60",
                    "--output",
                    str(output),
                ],
                text=True,
                capture_output=True,
            )
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
