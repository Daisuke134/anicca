import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
import re


APP_ROOT = Path(__file__).resolve().parents[1]


class InboxTerminalReportingTests(unittest.TestCase):
    def test_missing_private_env_is_terminal_and_preserves_exit_code(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_python = root / "python"
            fake_python.write_text(
                """#!/usr/bin/env python3
import json
import pathlib
import sys
argv = sys.argv[1:]
if argv[:3] == ["-m", "job_search_loop.application_reporting", "terminal"]:
    output = pathlib.Path(argv[argv.index("--output") + 1])
    run_id = argv[argv.index("--run-id") + 1]
    output.write_text(json.dumps({"delivery": "delivery_unknown", "event_key": f"job-search-inbox:{run_id}"}) + "\\n")
raise SystemExit(0)
""",
                encoding="utf-8",
            )
            fake_python.chmod(0o700)
            env = {
                **os.environ,
                "HOME": str(root / "home"),
                "JOB_SEARCH_STATE_ROOT": str(root / "state"),
                "JOB_SEARCH_PRIVATE_ENV": str(root / "missing.env"),
                "JOB_SEARCH_PYTHON": str(fake_python),
            }
            env.pop("GOG_KEYRING_PASSWORD", None)
            result = subprocess.run(
                ["/bin/zsh", str(APP_ROOT / "scripts" / "run-inbox.sh")],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )

            self.assertEqual(result.returncode, 78, result.stderr)
            evidence = next((root / "state" / "evidence").iterdir())
            receipt = json.loads((evidence / "inbox-terminal.json").read_text())
            self.assertEqual(receipt["delivery"], "delivery_unknown")
            self.assertRegex(
                receipt["event_key"],
                r"^job-search-inbox:inbox-\d{8}-\d{6}-\d+$",
            )
            self.assertEqual(oct((evidence / "inbox-terminal.json").stat().st_mode & 0o777), "0o600")


if __name__ == "__main__":
    unittest.main()
