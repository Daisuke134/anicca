import json
import os
import tempfile
import unittest
from pathlib import Path

from job_search_loop.browser_worker import (
    BrowserWorkerBusy,
    exclusive_worker,
    run_worker,
)
from job_search_loop.candidate_queue import CandidateQueue


class BrowserWorkerTests(unittest.TestCase):
    def test_daily_loop_consumes_route_fixture_before_models_or_live_browser_work(self):
        script = (
            Path(__file__).parents[1] / "scripts" / "run-daily.sh"
        ).read_text(encoding="utf-8")

        self.assertIn("route-fixture-request.json", script)
        self.assertIn("--route-fixture", script)
        fixture_branch = script.index('if [[ -f "$ROUTE_FIXTURE_REQUEST" ]]')
        model_call = script.index("job-search-terra-plan")
        self.assertLess(fixture_branch, model_call)
        self.assertIn('mv "$ROUTE_FIXTURE_REQUEST" "$EVIDENCE/route-fixture-request.json"', script)

    def test_run_worker_executes_route_fixture_with_resident_actor_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            owner_receipt = root / "browser-owner.json"
            owner_receipt.write_text(
                json.dumps(
                    {
                        "status": "ready",
                        "holder_pid": os.getpid(),
                        "lease_id": "lease-fixture",
                        "fence": 12,
                    }
                ),
                encoding="utf-8",
            )
            request = root / "route-fixture-request.json"
            request.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "request_id": "worker-fixture-1",
                        "application": {
                            "company": "Fixture Corp",
                            "title": "AI Engineer",
                            "url": "https://jobs.fixture.test/role",
                        },
                        "routes": [
                            {"kind": "canonical_ats", "endpoint": "https://jobs.fixture.test/role", "acceptance": "not_applicable"},
                            {"kind": "recruiting_email", "endpoint": "jobs@fixture.test", "acceptance": "accepts_applications"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            worker_receipt = root / "worker-receipt.json"

            result = run_worker(
                database=root / "candidate-queue.sqlite3",
                owner_receipt=owner_receipt,
                holder_pid=os.getpid(),
                run_id="daily-fixture",
                lock_path=root / "worker.lock",
                worker_receipt=worker_receipt,
                output=root / "result.json",
                evidence_dir=root / "evidence",
                route_fixture=request,
            )

            self.assertEqual(result["status"], "fixture_verified")
            self.assertEqual(result["send_count"], 0)
            self.assertEqual(result["actor_provenance"]["worker_pid"], os.getpid())
            recorded = json.loads(worker_receipt.read_text(encoding="utf-8"))
            self.assertEqual(recorded["actor"], "resident_worker")
            self.assertEqual(recorded["route_fixture_status"], "fixture_verified")

    def test_run_worker_invokes_one_release_contained_pre_submit_runner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "candidate-queue.sqlite3"
            queue = CandidateQueue(database)
            queue.close()
            owner_receipt = root / "browser-owner.json"
            owner_receipt.write_text(
                json.dumps(
                    {
                        "status": "ready",
                        "holder_pid": os.getpid(),
                        "lease_id": "lease-1",
                        "fence": 3,
                        "endpoint": "http://127.0.0.1:9222",
                    }
                ),
                encoding="utf-8",
            )
            prefilter = root / "prefilter.json"
            prefilter.write_text(json.dumps({"candidates": []}), encoding="utf-8")
            profile = root / "profile.json"
            profile.write_text(json.dumps({"candidate": {}}), encoding="utf-8")
            calls = []

            def fake_pre_submit_runner(**kwargs):
                calls.append(kwargs)
                return {
                    "status": "pending_verification",
                    "blocked": ["no_ranking_ready_candidate"],
                    "attempted_count": 3,
                }

            result = run_worker(
                database=database,
                owner_receipt=owner_receipt,
                holder_pid=os.getpid(),
                run_id="daily-test",
                lock_path=root / "worker.lock",
                worker_receipt=root / "worker-receipt.json",
                output=root / "result.json",
                prefilter_result=prefilter,
                profile_path=profile,
                materials_root=root / "materials",
                evidence_dir=root / "evidence",
                pre_submit_runner=fake_pre_submit_runner,
            )

            self.assertEqual(len(calls), 1)
            self.assertEqual(result["blocked"], ["no_ranking_ready_candidate"])
            self.assertEqual(result["attempted_count"], 3)

    def test_exclusive_worker_rejects_a_second_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / "browser-worker.lock"
            with exclusive_worker(lock):
                with self.assertRaisesRegex(BrowserWorkerBusy, "already running"):
                    with exclusive_worker(lock):
                        self.fail("second worker acquired the same lock")

    def test_run_worker_writes_truthful_pending_receipts_without_submission(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "candidate-queue.sqlite3"
            queue = CandidateQueue(database)
            try:
                queue.discover(
                    [
                        {
                            "url": "https://jobs.ashbyhq.com/example/role-1",
                            "source": "official_ats_boards",
                            "query_family": "dream",
                        }
                    ]
                )
            finally:
                queue.close()
            owner_receipt = root / "browser-owner.json"
            owner_receipt.write_text(
                json.dumps(
                    {
                        "status": "ready",
                        "holder_pid": os.getpid(),
                        "lease_id": "lease-1",
                        "fence": 7,
                    }
                ),
                encoding="utf-8",
            )
            output = root / "result.json"
            receipt = root / "worker-receipt.json"

            result = run_worker(
                database=database,
                owner_receipt=owner_receipt,
                holder_pid=os.getpid(),
                run_id="daily-test",
                lock_path=root / "worker.lock",
                worker_receipt=receipt,
                output=output,
            )

            self.assertEqual(result["submitted"], [])
            self.assertEqual(result["submit_unknown"], [])
            self.assertEqual(result["remaining_unverified_count"], 1)
            self.assertEqual(
                result["blocked"], ["1_candidate_links_await_fill_adapter"]
            )
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
            recorded = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(recorded["status"], "completed")
            self.assertEqual(recorded["fence"], 7)
            self.assertEqual(recorded["submitted_count"], 0)

    def test_run_worker_rejects_a_mismatched_daily_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            owner_receipt = root / "browser-owner.json"
            owner_receipt.write_text(
                json.dumps({"status": "ready", "holder_pid": 999999}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RuntimeError, "does not match"):
                run_worker(
                    database=root / "candidate-queue.sqlite3",
                    owner_receipt=owner_receipt,
                    holder_pid=os.getpid(),
                    run_id="daily-test",
                    lock_path=root / "worker.lock",
                    worker_receipt=root / "receipt.json",
                    output=root / "result.json",
                )


if __name__ == "__main__":
    unittest.main()
