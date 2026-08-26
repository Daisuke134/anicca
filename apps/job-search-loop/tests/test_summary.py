import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from job_search_loop.ledger import Ledger


class SummaryProjectionTests(unittest.TestCase):
    def test_v2_exposes_funnel_owners_ats_and_event_high_water(self):
        from job_search_loop import summary

        builder = getattr(summary, "build_summary_v2", None)
        self.assertIsNotNone(builder)

        def row(identifier, provider_url, stages):
            return {
                "application_id": identifier,
                "canonical_url": provider_url,
                "owner": "agent",
                "current_state": "submitted",
                "ever_submitted": True,
                "submission_attempted": True,
                "positive_funnel_stages": stages,
            }

        value = builder(
            day="2026-08-24",
            applications=[
                row(
                    "one",
                    "https://example.wd5.myworkdayjobs.com/job/one",
                    ["confirmed_application", "recruiter_response", "interview"],
                ),
                row(
                    "two",
                    "https://jobs.ashbyhq.com/example/two",
                    ["confirmed_application"],
                ),
                row("three", "https://jobs.example/three", []),
            ],
            event_high_water=17,
        )

        self.assertEqual(value["version"], 2)
        self.assertEqual(value["event_high_water"], 17)
        self.assertEqual(value["owners"], {"agent": 3})
        self.assertEqual(
            value["funnel"]["interview_rate"],
            {"numerator": 1, "denominator": 2, "rate": 0.5},
        )
        self.assertRegex(value["projection_sha256"], r"^[a-f0-9]{64}$")

    def test_cli_writes_v2_and_v1_from_one_event_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "ledger.sqlite3"
            output = root / "summary.v2.json"
            compatibility = root / "summary.v1.json"
            ledger = Ledger(database)
            workday = ledger.add_application(
                "Private Workday Employer",
                "Private AI Role",
                "https://example.wd5.myworkdayjobs.com/job/42",
            )
            ashby = ledger.add_application(
                "Private Ashby Employer",
                "Private Product Role",
                "https://jobs.ashbyhq.com/example/role/application",
            )
            for application_id, terminal in (
                (workday, "submitted"),
                (ashby, "submit_unknown"),
            ):
                for state in ("qualified", "materials_ready", "submit_claimed"):
                    ledger.transition(application_id, state)
                ledger.transition(application_id, terminal)
            high_water = ledger.connection.execute(
                "SELECT COALESCE(MAX(rowid),0) FROM events"
            ).fetchone()[0]
            ledger.close()

            command = [
                sys.executable,
                "-m",
                "job_search_loop.summary",
                "--ledger",
                str(database),
                "--output",
                str(output),
                "--compat-output",
                str(compatibility),
                "--day",
                "2026-08-24",
                "--model-route",
                "codex",
            ]
            first = subprocess.run(
                command, check=False, capture_output=True, text=True
            )

            self.assertEqual(first.returncode, 0, first.stderr)
            v2 = json.loads(output.read_text(encoding="utf-8"))
            v1 = json.loads(compatibility.read_text(encoding="utf-8"))
            self.assertEqual(v2["version"], 2)
            self.assertEqual(v1["version"], 1)
            self.assertEqual(v2["event_high_water"], high_water)
            self.assertEqual(v2["counts"], v1["counts"])
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(compatibility.stat().st_mode & 0o777, 0o600)
            first_v2 = output.read_bytes()
            first_v1 = compatibility.read_bytes()

            second = subprocess.run(
                command, check=False, capture_output=True, text=True
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(output.read_bytes(), first_v2)
            self.assertEqual(compatibility.read_bytes(), first_v1)
            encoded = json.dumps(v2).casefold()
            self.assertNotIn("private workday employer", encoded)
            self.assertNotIn("private ai role", encoded)
            self.assertNotIn("https://", encoded)

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
                        "required_adapters": [
                            "ashby", "greenhouse", "lever", "workday", "generic"
                        ],
                        "confirmed_adapters": ["ashby", "generic"],
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
