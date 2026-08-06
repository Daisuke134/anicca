import json
import os
import tempfile
import unittest
from pathlib import Path

from job_search_loop.route_fixture import run_no_send_fixture


class RouteFixtureTests(unittest.TestCase):
    def test_resident_fixture_advances_every_route_and_crash_replay_stays_fenced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request = root / "request.json"
            request.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "request_id": "fixture-001",
                        "application": {
                            "company": "Fixture Corp",
                            "title": "AI Engineer",
                            "url": "https://jobs.fixture.test/role",
                        },
                        "routes": [
                            {"kind": "canonical_ats", "endpoint": "https://jobs.fixture.test/role", "acceptance": "not_applicable"},
                            {"kind": "alternate_official", "endpoint": "https://careers.fixture.test/role", "acceptance": "not_applicable"},
                            {"kind": "recruiting_email", "endpoint": "jobs@fixture.test", "acceptance": "accepts_applications"},
                            {"kind": "recruiting_outreach", "endpoint": "talent@fixture.test", "acceptance": "outreach_only"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            result = run_no_send_fixture(
                request_path=request,
                evidence_dir=root / "evidence",
                authority={
                    "actor": "resident_worker",
                    "worker_pid": os.getpid(),
                    "run_id": "daily-fixture",
                    "lease_id": "lease-1",
                    "fence": 9,
                },
            )

            self.assertEqual(result["status"], "fixture_verified")
            self.assertEqual(result["send_count"], 0)
            self.assertEqual(
                [item["route_kind"] for item in result["ordered_attempts"]],
                ["canonical_ats", "alternate_official", "recruiting_email", "recruiting_outreach"],
            )
            self.assertTrue(all(item["state"] == "failed" for item in result["ordered_attempts"]))
            self.assertEqual(result["replay_status"], "no_eligible_route")
            self.assertEqual(result["ats_crash_replay_status"], "ats_action_fenced")
            self.assertEqual(result["email_fallback_status"], "email_claimed")
            self.assertEqual(result["actor_provenance"]["actor"], "resident_worker")
            self.assertEqual(result["actor_provenance"]["worker_pid"], os.getpid())

    def test_direct_development_actor_cannot_run_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request = root / "request.json"
            request.write_text(
                json.dumps({"version": 1, "request_id": "fixture-002", "application": {}, "routes": []}),
                encoding="utf-8",
            )
            for actor in ("codex", "claude", "shell", "python"):
                with self.subTest(actor=actor), self.assertRaisesRegex(RuntimeError, "resident worker"):
                    run_no_send_fixture(
                        request_path=request,
                        evidence_dir=root / actor,
                        authority={"actor": actor, "worker_pid": os.getpid()},
                    )


if __name__ == "__main__":
    unittest.main()
