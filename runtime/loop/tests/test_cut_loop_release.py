import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


class CutLoopReleaseTest(unittest.TestCase):
    def test_sparse_release_leaves_global_current_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            loops = root / "loops"
            sentinel = root / "full-release"
            sentinel.mkdir()
            loops.mkdir()
            current = loops / "current"
            current.symlink_to(sentinel)

            result = subprocess.run(
                ["/bin/bash", str(ROOT / "bin/cut-loop-release.sh"), "origin/main"],
                cwd=ROOT,
                env={
                    **os.environ,
                    "LOOPS_ROOT": str(loops),
                    "LOOPS_KEEP_RELEASES": "1",
                    "LOOPS_RELEASE_PATHS": "bin runtime/loop config/loop-registry.json",
                },
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(current.resolve(), sentinel.resolve())
            self.assertIn("current unchanged", result.stdout)

    def test_release_builds_locked_root_and_agentmail_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
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
                    "LIFE_MANAGER_LAUNCH_AGENTS_DIR": str(agents),
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
            self.assertIn("/apps/life-manager|ci --omit=dev --ignore-scripts", recorded[2])


if __name__ == "__main__":
    unittest.main()
