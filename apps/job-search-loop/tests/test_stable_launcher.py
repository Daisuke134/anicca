import os
import subprocess
import tempfile
import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]


class StableLauncherTests(unittest.TestCase):
    def test_installed_launcher_fails_closed_then_executes_immutable_current_release(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            libexec = root / "libexec"
            data = root / "data"
            env = {
                **os.environ,
                "JOB_SEARCH_LIBEXEC_ROOT": str(libexec),
                "JOB_SEARCH_DATA_ROOT": str(data),
            }
            installed = subprocess.run(
                ["/bin/zsh", str(APP_ROOT / "scripts/install-stable-launchers.sh")],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(installed.returncode, 0, installed.stderr)
            self.assertEqual(sorted(path.name for path in libexec.iterdir()), ["daily", "inbox", "learning"])
            self.assertTrue(all(path.stat().st_mode & 0o222 == 0 for path in libexec.iterdir()))
            inactive = subprocess.run([str(libexec / "daily")], capture_output=True, text=True, env=env)
            self.assertEqual(inactive.returncode, 78)
            self.assertIn("data root is missing", inactive.stderr)

            release = data / "releases" / "commit-1"
            scripts = release / "apps/job-search-loop/scripts"
            scripts.mkdir(parents=True)
            (release / "RELEASE.json").write_text("{}", encoding="utf-8")
            runner = scripts / "run-daily.sh"
            runner.write_text("#!/bin/zsh\nprint -r -- executed:$1\n", encoding="utf-8")
            runner.chmod(0o755)
            (data / "current").symlink_to(release)
            for path in sorted(release.rglob("*"), reverse=True):
                path.chmod(0o555 if path.is_dir() or path == runner else 0o444)
            release.chmod(0o555)
            active = subprocess.run([str(libexec / "daily"), "proof"], capture_output=True, text=True, env=env)
            self.assertEqual(active.returncode, 0, active.stderr)
            self.assertEqual(active.stdout.strip(), "executed:proof")


if __name__ == "__main__":
    unittest.main()
