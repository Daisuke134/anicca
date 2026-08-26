import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]


class MercorTerminalReportingTests(unittest.TestCase):
    def test_runner_failure_writes_private_terminal_receipt_and_one_unknown_delivery(self):
        """Removing Mercor finalization must fail this runner-failure wake."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            calls = root / "calls.jsonl"
            fake_python = root / "python"
            fake_python.write_text(
                """#!/usr/bin/env python3
import json
import os
import pathlib
import sys

calls = pathlib.Path(os.environ["MERCOR_TEST_CALLS"])
argv = sys.argv[1:]
calls.write_text(calls.read_text() + json.dumps(argv) + "\\n" if calls.exists() else json.dumps(argv) + "\\n")
if argv[:2] == ["-m", "job_search_loop.browser_owner"]:
    output = pathlib.Path(argv[argv.index("--output") + 1])
    output.write_text('{"status":"ready"}\\n')
    raise SystemExit(0)
if argv[:2] == ["-m", "job_search_loop.mercor_pass"]:
    raise SystemExit(1)
if argv[:2] == ["-m", "job_search_loop.mercor_earnings_capture"]:
    output = pathlib.Path(argv[argv.index("--output") + 1])
    output.write_text('{"status":"empty","rows":[]}\\n')
    raise SystemExit(0)
if argv[:2] == ["-m", "job_search_loop.mercor_earnings_sync"]:
    output = pathlib.Path(argv[argv.index("--output") + 1])
    output.write_text('{"status":"not_observed"}\\n')
    raise SystemExit(0)
if argv[:2] == ["-m", "job_search_loop.mercor_reporting"]:
    if os.environ.get("MERCOR_TEST_REPORTING_FAIL") == "1":
        raise SystemExit(1)
    result = pathlib.Path(argv[argv.index("--result") + 1])
    terminal = pathlib.Path(argv[argv.index("--terminal") + 1])
    output = pathlib.Path(argv[argv.index("--output") + 1])
    run_id = argv[argv.index("--run-id") + 1]
    terminal.parent.mkdir(parents=True, exist_ok=True)
    terminal.write_text(json.dumps({"status": "failed"}) + "\\n")
    terminal.chmod(0o600)
    output.write_text(json.dumps({"delivery":"delivery_unknown", "event_key": f"mercor-pass:{run_id}"}) + "\\n")
    raise SystemExit(0)
raise SystemExit(0)
""",
                encoding="utf-8",
            )
            fake_python.chmod(0o700)
            resume = root / "materials" / "resume.pdf"
            resume.parent.mkdir()
            resume.write_bytes(b"%PDF-1.4\n")
            resume_state = root / "state" / "mercor" / "resume-state.json"
            resume_state.parent.mkdir(parents=True)
            resume_state.write_text(
                json.dumps({"resume_file": str(resume)}) + "\n",
                encoding="utf-8",
            )
            env = {
                **os.environ,
                "HOME": str(root / "home"),
                "XDG_CONFIG_HOME": str(root / "config"),
                "XDG_DATA_HOME": str(root / "data"),
                "JOB_SEARCH_STATE_ROOT": str(root / "state"),
                "JOB_SEARCH_PYTHON": str(fake_python),
                "MERCOR_TEST_CALLS": str(calls),
            }
            result = subprocess.run(
                ["/bin/zsh", str(APP_ROOT / "scripts" / "run-mercor.sh")],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            evidence = next((root / "state" / "evidence").iterdir())
            terminal = evidence / "mercor-pass-terminal.json"
            report = evidence / "telegram-report.json"
            self.assertEqual(json.loads(terminal.read_text())["status"], "failed")
            self.assertEqual(oct(terminal.stat().st_mode & 0o777), "0o600")
            receipt = json.loads(report.read_text())
            self.assertEqual(receipt["delivery"], "delivery_unknown")
            self.assertEqual(receipt["event_key"], f"mercor-pass:{evidence.name}")
            reporting_calls = [
                json.loads(line)
                for line in calls.read_text().splitlines()
                if json.loads(line)[:2] == ["-m", "job_search_loop.mercor_reporting"]
            ]
            self.assertEqual(len(reporting_calls), 1)
            pass_call = next(
                json.loads(line)
                for line in calls.read_text().splitlines()
                if json.loads(line)[:2] == ["-m", "job_search_loop.mercor_pass"]
            )
            self.assertEqual(pass_call[pass_call.index("--resume") + 1], str(resume))

    def test_reporting_module_failure_still_writes_private_terminal_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_python = root / "python"
            fake_python.write_text(
                """#!/usr/bin/env python3
import os
import pathlib
import sys
argv = sys.argv[1:]
if argv[:2] == ["-m", "job_search_loop.browser_owner"]:
    pathlib.Path(argv[argv.index("--output") + 1]).write_text("{}\\n")
    raise SystemExit(0)
if argv[:2] == ["-m", "job_search_loop.mercor_pass"]:
    raise SystemExit(1)
if argv[:2] == ["-m", "job_search_loop.mercor_reporting"]:
    raise SystemExit(1)
raise SystemExit(0)
""",
                encoding="utf-8",
            )
            fake_python.chmod(0o700)
            result = subprocess.run(
                ["/bin/zsh", str(APP_ROOT / "scripts" / "run-mercor.sh")],
                check=False,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    "HOME": str(root / "home"),
                    "XDG_DATA_HOME": str(root / "data"),
                    "JOB_SEARCH_STATE_ROOT": str(root / "state"),
                    "JOB_SEARCH_PYTHON": str(fake_python),
                },
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            evidence = next((root / "state" / "evidence").iterdir())
            terminal = json.loads((evidence / "mercor-pass-terminal.json").read_text())
            self.assertEqual(terminal["status"], "failed")
            self.assertEqual(oct((evidence / "mercor-pass-terminal.json").stat().st_mode & 0o777), "0o600")


if __name__ == "__main__":
    unittest.main()
