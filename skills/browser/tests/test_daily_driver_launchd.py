import plistlib
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[3]
RENDER = ROOT / "skills/browser/render-launchd.sh"

class DailyDriverLaunchdTests(unittest.TestCase):
    def test_renderer_emits_one_direct_persistent_owner(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            profile = home / ".cloak/profiles/daily-driver"
            profile.mkdir(parents=True)
            python = home / "venv/bin/python3"
            python.parent.mkdir(parents=True)
            python.write_text("#!/bin/sh\n", encoding="utf-8")
            python.chmod(0o755)
            output = home / "rendered"
            result = subprocess.run([
                "bash", str(RENDER), "--output-dir", str(output), "--repo-root", str(ROOT),
                "--life-manager-home", str(home / "state"), "--cloak-python", str(python),
                "--profile", str(profile),
            ], env={"HOME": str(home), "PATH": "/usr/bin:/bin"}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            plist = plistlib.loads((output / "ai.anicca.life-manager-daily-driver.plist").read_bytes())
            self.assertEqual(plist["Label"], "ai.anicca.life-manager-daily-driver")
            self.assertTrue(plist["KeepAlive"])
            self.assertEqual(plist["ProgramArguments"], [str(python), str(ROOT / "skills/browser/cdp_persistent_context.py"), "--profile", str(profile), "--port", "9222"])
            self.assertNotIn("StartInterval", plist)
            self.assertNotIn("StartCalendarInterval", plist)

if __name__ == "__main__":
    unittest.main()
