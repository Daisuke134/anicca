import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


class CutLoopReleaseTest(unittest.TestCase):
    def test_release_builds_locked_root_and_agentmail_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            remote = root / "remote.git"
            subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
            subprocess.run(
                ["git", "init", "-b", "main", str(source)],
                check=True,
                capture_output=True,
            )
            manifest = '{"name":"release-fixture","version":"1.0.0"}\n'
            lock = (
                '{"name":"release-fixture","version":"1.0.0","lockfileVersion":3,'
                '"requires":true,"packages":{"":{"name":"release-fixture","version":"1.0.0"}}}\n'
            )
            for package_dir in [source, source / "runtime/agentmail", source / "apps/mr-bot"]:
                package_dir.mkdir(parents=True, exist_ok=True)
                (package_dir / "package.json").write_text(manifest)
                (package_dir / "package-lock.json").write_text(lock)
            subprocess.run(["git", "add", "."], cwd=source, check=True, capture_output=True)
            subprocess.run(
                [
                    "git", "-c", "user.name=Release Test", "-c", "user.email=release@example.test",
                    "commit", "-m", "fixture",
                ],
                cwd=source,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "remote", "add", "origin", str(remote)],
                cwd=source,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "push", "-u", "origin", "main"],
                cwd=source,
                check=True,
                capture_output=True,
            )
            calls = root / "npm.calls"
            npm = root / "npm"
            npm.write_text(
                f'#!/bin/sh\nprintf "%s|%s\\n" "$PWD" "$*" >> "{calls}"\n'
                'mkdir -p node_modules\n')
            npm.chmod(0o755)
            agents = root / "agents"
            agents.mkdir()
            result = subprocess.run(
                ["/bin/bash", str(ROOT / "bin/cut-loop-release.sh"), "origin/main"],
                cwd=ROOT,
                env={
                    **os.environ,
                    "LOOPS_ROOT": str(root / "loops"),
                    "LOOPS_KEEP_RELEASES": "1",
                    "MR_BOT_LAUNCH_AGENTS_DIR": str(agents),
                    "MR_BOT_SOURCE_REPO": str(source),
                    "NPM_BIN": str(npm),
                },
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            recorded = calls.read_text().splitlines()
            self.assertEqual(len(recorded), 3)
            self.assertTrue(recorded[0].endswith("|ci --omit=dev --ignore-scripts"))
            self.assertIn("/runtime/agentmail|ci --omit=dev --ignore-scripts", recorded[1])
            self.assertIn("/apps/mr-bot|ci --omit=dev --ignore-scripts", recorded[2])


if __name__ == "__main__":
    unittest.main()
