import json
import tempfile
import unittest
from pathlib import Path

from job_search_loop.release_activation import ActivationError, activate, rollback


class ReleaseActivationTests(unittest.TestCase):
    def _release(self, data: Path, commit: str) -> Path:
        release = data / "releases" / commit
        scripts = release / "apps/job-search-loop/scripts"
        scripts.mkdir(parents=True)
        (release / "RELEASE.json").write_text(json.dumps({"commit": commit}), encoding="utf-8")
        config = release / "runtime/agent-runner/config.json"
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({"version": 1, "routes": []}), encoding="utf-8")
        for lane in ("browser", "daily", "inbox", "learning"):
            runner = scripts / f"run-{lane}.sh"
            runner.write_text("#!/bin/zsh\nexit 0\n", encoding="utf-8")
            runner.chmod(0o555)
        for path in sorted(release.rglob("*"), reverse=True):
            path.chmod(0o555 if path.is_dir() else path.stat().st_mode & ~0o222)
        release.chmod(0o555)
        return release

    def test_activation_retains_previous_and_rolls_back_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "job-search"
            old = self._release(data, "old-commit")
            new = self._release(data, "new-commit")

            activate(data_root=data, commit="old-commit")
            self.assertEqual(
                json.loads((data / "active-release.json").read_text())["active_commit"],
                "old-commit",
            )
            self.assertEqual((data / "active-release.json").stat().st_mode & 0o777, 0o600)
            activate(data_root=data, commit="new-commit")
            self.assertEqual((data / "current").resolve(), new.resolve())
            self.assertEqual((data / "previous").resolve(), old.resolve())

            receipt = rollback(data_root=data)
            self.assertEqual((data / "current").resolve(), old.resolve())
            self.assertEqual((data / "previous").resolve(), new.resolve())
            self.assertEqual(receipt["active_commit"], "old-commit")
            self.assertEqual(receipt["rollback_from_commit"], "new-commit")
            self.assertEqual(
                json.loads((data / "active-release.json").read_text())["active_commit"],
                "old-commit",
            )

    def test_writable_candidate_is_rejected_before_pointer_change(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "job-search"
            good = self._release(data, "good-commit")
            bad = self._release(data, "bad-commit")
            activate(data_root=data, commit="good-commit")
            bad.chmod(0o755)

            with self.assertRaisesRegex(ActivationError, "writable"):
                activate(data_root=data, commit="bad-commit")
            self.assertEqual((data / "current").resolve(), good.resolve())


if __name__ == "__main__":
    unittest.main()
