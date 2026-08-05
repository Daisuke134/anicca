import json
import tempfile
import unittest
from pathlib import Path

from job_search_loop.guardian import GuardianError, release_health
from job_search_loop.release_activation import activate


class GuardianReleaseTests(unittest.TestCase):
    def launchers(self, data):
        root = data / "launchers"
        root.mkdir(parents=True)
        for lane in ("browser", "daily", "inbox", "learning"):
            launcher = root / lane
            launcher.write_text("#!/bin/zsh\nexit 0\n")
            launcher.chmod(0o555)
        return root

    def release(self, data, commit):
        root = data / "releases" / commit
        scripts = root / "apps/job-search-loop/scripts"
        scripts.mkdir(parents=True)
        (root / "RELEASE.json").write_text(json.dumps({"commit": commit}))
        config = root / "runtime/agent-runner/config.json"
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({"version": 1}))
        for lane in ("browser", "daily", "inbox", "learning"):
            runner = scripts / f"run-{lane}.sh"
            runner.write_text("#!/bin/zsh\nexit 0\n")
            runner.chmod(0o555)
        for path in sorted(root.rglob("*"), reverse=True):
            path.chmod(0o555 if path.is_dir() else path.stat().st_mode & ~0o222)
        root.chmod(0o555)
        return root

    def test_active_receipt_release_and_runners_must_all_agree(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "job-search"
            self.release(data, "commit-one")
            launchers = self.launchers(data)
            activate(data_root=data, commit="commit-one")
            report = release_health(data, launchers)
            self.assertEqual(report["status"], "healthy")
            self.assertEqual(report["active_commit"], "commit-one")
            self.assertEqual(report["runner_count"], 4)

    def test_receipt_tamper_or_writable_release_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "job-search"
            release = self.release(data, "commit-one")
            launchers = self.launchers(data)
            activate(data_root=data, commit="commit-one")
            receipt = data / "active-release.json"
            value = json.loads(receipt.read_text())
            value["active_commit"] = "other"
            receipt.write_text(json.dumps(value))
            with self.assertRaises(GuardianError):
                release_health(data, launchers)
            activate(data_root=data, commit="commit-one")
            release.chmod(0o755)
            with self.assertRaisesRegex(GuardianError, "writable"):
                release_health(data, launchers)


if __name__ == "__main__":
    unittest.main()
