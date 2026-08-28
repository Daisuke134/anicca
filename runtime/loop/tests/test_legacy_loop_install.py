import os
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


class LegacyLoopInstallTest(unittest.TestCase):
    def test_legacy_installer_is_tombstone_without_launchctl_or_home_mutation(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            bin_dir = root / "bin"
            home = root / "home"
            bin_dir.mkdir()
            home.mkdir()
            script = bin_dir / "loop-install.sh"
            shutil.copy2(ROOT / "bin/loop-install.sh", script)
            calls = root / "launchctl.calls"
            launchctl_safe = bin_dir / "launchctl-safe"
            launchctl_safe.write_text(
                "#!/bin/sh\n"
                f"printf '%s\\n' \"$*\" >> {shlex.quote(str(calls))}\n"
                "exit 0\n"
            )
            launchctl_safe.chmod(0o755)

            result = subprocess.run(
                ["bash", str(script), "example"],
                env={**os.environ, "HOME": str(home)},
                capture_output=True,
                text=True,
                timeout=10,
            )

            self.assertEqual(result.returncode, 64)
            self.assertIn("lm-loop apply", result.stdout + result.stderr)
            self.assertFalse(calls.exists())
            self.assertEqual(list(home.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
