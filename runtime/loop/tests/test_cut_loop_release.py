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
            calls = root / "npm.calls"
            npm = root / "npm"
            npm.write_text(
                f'#!/bin/sh\nprintf "%s|%s\\n" "$PWD" "$*" >> "{calls}"\n'
                'mkdir -p node_modules\n')
            npm.chmod(0o755)
            agents = root / "agents"
            agents.mkdir()
            result = subprocess.run(
                ["/bin/bash", str(ROOT / "bin/cut-loop-release.sh"), "HEAD"],
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
            self.assertEqual(len(recorded), 2)
            self.assertTrue(recorded[0].endswith("|ci --omit=dev --ignore-scripts"))
            self.assertIn("/runtime/agentmail|ci --omit=dev --ignore-scripts", recorded[1])


if __name__ == "__main__":
    unittest.main()
