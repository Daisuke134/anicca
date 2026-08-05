import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from job_search_loop.ledger import Ledger


class SummaryProjectionTests(unittest.TestCase):
    def test_cli_writes_private_adapter_progress_without_application_details(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "ledger.sqlite3"
            output = root / "summary.v2.json"
            ledger = Ledger(database)
            applications = [
                (
                    ledger.add_application(
                        "Ashby Employer",
                        "Applied AI Engineer",
                        "https://jobs.ashbyhq.com/example/ashby-role/application",
                    ),
                    "submitted",
                ),
                (
                    ledger.add_application(
                        "Workday Employer",
                        "AI Solutions Consultant",
                        "https://example.wd5.myworkdayjobs.com/careers/job/42",
                    ),
                    "submit_unknown",
                ),
                (
                    ledger.add_application(
                        "Generic Employer",
                        "AI Product Manager",
                        "https://careers.example.com/jobs/7",
                    ),
                    "submitted",
                ),
                (
                    ledger.add_application(
                        "Progressed Ashby Employer",
                        "AI Partnerships Lead",
                        "https://jobs.ashbyhq.com/example/progressed-role/application",
                    ),
                    "interview",
                ),
            ]
            for application_id, state in applications:
                for transition in ("qualified", "materials_ready", "submit_claimed"):
                    ledger.transition(application_id, transition)
                if state == "interview":
                    ledger.transition(application_id, "submitted")
                    ledger.transition(application_id, "interview")
                else:
                    ledger.transition(application_id, state)
            ledger.close()

            output.write_text("{partial", encoding="utf-8")
            output.chmod(0o644)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "job_search_loop.summary",
                    "--ledger",
                    str(database),
                    "--output",
                    str(output),
                    "--day",
                    "2026-07-29",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.is_file())
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(
                [
                    path.name
                    for path in root.iterdir()
                    if path.name.startswith(".summary.v2.json.")
                ],
                [],
            )
            value = json.loads(output.read_text(encoding="utf-8"))
            first_bytes = output.read_bytes()
            self.assertEqual(value["version"], 2)
            self.assertEqual(value["day"], "2026-07-29")
            self.assertEqual(
                value["counts"],
                {
                    "interview": 1,
                    "submit_unknown": 1,
                    "submitted": 2,
                },
            )
            self.assertEqual(value["owners"], {"agent": 4})
            self.assertEqual(
                value["ats_progress"],
                {
                    "required_adapters": ["ashby", "workday"],
                    "confirmed_adapters": ["ashby"],
                    "complete": False,
                    "adapters": {
                        "ashby": {"ever_submitted": 2, "interview": 1, "submitted": 1},
                        "generic": {"ever_submitted": 1, "submitted": 1},
                        "workday": {"submit_unknown": 1},
                    },
                },
            )
            self.assertRegex(value["projection_sha256"], r"^[a-f0-9]{64}$")
            self.assertNotIn("model_route", value)
            output.unlink()
            replay = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "job_search_loop.summary",
                    "--ledger",
                    str(database),
                    "--output",
                    str(output),
                    "--day",
                    "2026-07-29",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(replay.returncode, 0, replay.stderr)
            self.assertEqual(output.read_bytes(), first_bytes)
            ledger = Ledger(database)
            try:
                with self.assertRaises(sqlite3.IntegrityError):
                    ledger.connection.execute(
                        "UPDATE events SET to_state='rejected'"
                    )
                with self.assertRaises(sqlite3.IntegrityError):
                    ledger.connection.execute("DELETE FROM events")
                with self.assertRaises(sqlite3.IntegrityError):
                    ledger.connection.execute(
                        "UPDATE applications SET current_state='rejected'"
                    )
            finally:
                ledger.close()
            encoded = json.dumps(value).casefold()
            for private_value in (
                "ashby employer",
                "workday employer",
                "generic employer",
                "applied ai engineer",
                "https://",
            ):
                self.assertNotIn(private_value, encoded)


if __name__ == "__main__":
    unittest.main()
