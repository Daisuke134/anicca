import json
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
            output = root / "summary.v1.json"
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
            with ledger._transaction():
                for application_id, state in applications:
                    ledger.connection.execute(
                        "UPDATE applications SET current_state=? WHERE id=?",
                        (state, application_id),
                    )
                ledger.connection.execute(
                    """
                    INSERT INTO submit_intents
                      (intent_id, application_id, fence, payload_hash, japan_day,
                       slot, status, created_at)
                    VALUES
                      ('progressed-intent', ?, 1, 'payload', '2026-07-28',
                       1, 'submitted', '2026-07-28T00:00:00+00:00')
                    """,
                    (applications[-1][0],),
                )
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
                    "--model-route",
                    "codex",
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
                    if path.name.startswith(".summary.v1.json.")
                ],
                [],
            )
            value = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(
                value,
                {
                    "version": 1,
                    "day": "2026-07-29",
                    "counts": {
                        "interview": 1,
                        "submit_unknown": 1,
                        "submitted": 2,
                    },
                    "model_route": "codex",
                    "ats_progress": {
                        "required_adapters": ["ashby", "workday"],
                        "confirmed_adapters": ["ashby"],
                        "complete": False,
                        "adapters": {
                            "ashby": {"submitted": 2},
                            "generic": {"submitted": 1},
                            "workday": {"submit_unknown": 1},
                        },
                    },
                },
            )
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
