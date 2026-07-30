import importlib.util
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gig_slo.py"


def load():
    spec = importlib.util.spec_from_file_location("gig_slo_collector_under_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load gig_slo")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GigSloCollectorTest(unittest.TestCase):
    def setUp(self):
        self.slo = load()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "state/lanes").mkdir(parents=True)
        self.now = 2_000_000
        heartbeat = self.root / ".last-pass"
        heartbeat.write_text("pass-1\n")
        os.utime(heartbeat, (self.now - 1800, self.now - 1800))
        for lane in ("apply", "reply", "fulfill", "list"):
            (self.root / f"state/lanes/{lane}.json").write_text(json.dumps({
                "last_attempt_at": self.now - 1800,
                "last_productive_at": self.now - 7200,
                "barren_streak": 0,
            }))
        self.telegram = self.root / "telegram.sqlite3"
        self.host_state = self.root / "host-state"
        self.host_state.mkdir()
        with sqlite3.connect(self.telegram) as connection:
            connection.execute("""CREATE TABLE telegram_reports(
                report_id INTEGER PRIMARY KEY, kind TEXT, state TEXT, created_at INTEGER
            )""")
            connection.execute(
                "INSERT INTO telegram_reports VALUES(1,'pass','sent',?)",
                (self.now - 1700,),
            )

    def test_collects_authoritative_files_and_outbox(self):
        snapshot = self.slo.collect_snapshot(
            state_dir=self.root,
            telegram_database=self.telegram,
            now=self.now,
        )
        self.assertEqual(snapshot["last_pass_at"], self.now - 1800)
        self.assertEqual(snapshot["lanes"]["apply"]["barren_streak"], 0)
        self.assertEqual(snapshot["telegram"]["latest_pass_state"], "sent")
        self.assertEqual(snapshot["telegram"]["delivery_unknown"], 0)
        self.assertEqual(snapshot["telegram"]["delivery_unknown_active"], 0)

    def test_collects_disk_stop_and_pressure_as_separate_signals(self):
        (self.host_state / "disk-writers.stop").write_text("hard stop\n")
        (self.host_state / "disk-pressure.block").write_text(
            "free_gb=8 threshold_gb=11\n"
        )
        snapshot = self.slo.collect_snapshot(
            state_dir=self.root,
            telegram_database=self.telegram,
            host_state_dir=self.host_state,
            now=self.now,
        )
        self.assertTrue(snapshot["disk"]["hard_stop"])
        self.assertTrue(snapshot["disk"]["pressure_advisory"])
        self.assertEqual(snapshot["disk"]["minimum_free_gb"], 5)

    def test_historical_delivery_unknown_is_visible_but_not_active(self):
        with sqlite3.connect(self.telegram) as connection:
            connection.execute(
                "INSERT INTO telegram_reports VALUES(2,'pass','delivery_unknown',?)",
                (self.now - self.slo.RECENT_FAILURE_SECONDS - 1,),
            )
        snapshot = self.slo.collect_snapshot(
            state_dir=self.root,
            telegram_database=self.telegram,
            now=self.now,
        )
        self.assertEqual(snapshot["telegram"]["delivery_unknown"], 1)
        self.assertEqual(snapshot["telegram"]["delivery_unknown_active"], 0)

    def test_recent_delivery_unknown_is_active(self):
        with sqlite3.connect(self.telegram) as connection:
            connection.execute(
                "INSERT INTO telegram_reports VALUES(2,'pass','delivery_unknown',?)",
                (self.now - 60,),
            )
        snapshot = self.slo.collect_snapshot(
            state_dir=self.root,
            telegram_database=self.telegram,
            now=self.now,
        )
        self.assertEqual(snapshot["telegram"]["delivery_unknown"], 1)
        self.assertEqual(snapshot["telegram"]["delivery_unknown_active"], 1)

    def test_recent_failure_ledger_is_bounded_by_time(self):
        (self.root / "pass-failures.jsonl").write_text(
            json.dumps({"ts": self.now - 60, "reason": "browser_cdp_unavailable"}) + "\n"
            + json.dumps({"ts": self.now - 99999, "reason": "old"}) + "\n"
        )
        snapshot = self.slo.collect_snapshot(
            state_dir=self.root,
            telegram_database=self.telegram,
            now=self.now,
        )
        self.assertEqual(len(snapshot["recent_failures"]), 1)
        self.assertEqual(snapshot["recent_failures"][0]["reason"], "browser_cdp_unavailable")

    def _agent_failure(
        self,
        *,
        summary: dict,
        attempt: dict | None = None,
        stdout: str = "",
    ) -> None:
        evidence = self.root / "evidence" / "gig-pass-pass-2"
        agent = evidence / "agent-B2"
        agent.mkdir(parents=True)
        (agent / "summary.json").write_text(json.dumps(summary))
        if attempt is not None:
            (agent / "attempts.jsonl").write_text(json.dumps(attempt) + "\n")
            (agent / "attempt-01.stdout.log").write_text(stdout)
        (self.root / "pass-failures.jsonl").write_text(json.dumps({
            "ts": self.now - 60,
            "reason": "agent_step_failed",
            "failed_step": "B2",
            "pass_id": "pass-2",
            "evidence_dir": str(evidence),
        }) + "\n")

    def test_agent_failure_uses_attempt_evidence_to_identify_strict_schema(self):
        self._agent_failure(
            summary={"status": "failed"},
            attempt={
                "rc": 1,
                "timed_out": False,
                "stdout_path": "ignored-untrusted-path",
                "error_class": "validation_or_task_failure",
            },
            stdout=(
                '{"code":"invalid_json_schema","message":'
                '"Invalid schema for response_format"}'
            ),
        )
        snapshot = self.slo.collect_snapshot(
            state_dir=self.root,
            telegram_database=self.telegram,
            now=self.now,
        )
        failure = snapshot["recent_failures"][0]
        self.assertEqual(failure["diagnosis_class"], "schema_invalid")
        incidents = self.slo.evaluate(snapshot, now=self.now)
        self.assertIn(
            {
                "fingerprint": "schema:invalid_result:B2",
                "repair_class": "schema_diagnose",
                "evidence": {
                    "ts": self.now - 60,
                    "failed_step": "B2",
                    "reason": "agent_step_failed",
                    "diagnosis_class": "schema_invalid",
                    "diagnosis_evidence": {
                        "summary_status": "failed",
                        "attempt_rc": 1,
                        "attempt_timed_out": False,
                        "attempt_error_class": "validation_or_task_failure",
                        "attempt_executable": None,
                    },
                },
            },
            incidents,
        )

    def test_budget_block_is_not_misclassified_as_provider_outage(self):
        self._agent_failure(summary={
            "status": "budget_blocked",
            "budget": {"status": "blocked", "reason": "pass_token_budget_exceeded"},
        })
        snapshot = self.slo.collect_snapshot(
            state_dir=self.root,
            telegram_database=self.telegram,
            now=self.now,
        )
        self.assertEqual(
            snapshot["recent_failures"][0]["diagnosis_class"],
            "budget_policy",
        )
        incidents = self.slo.evaluate(snapshot, now=self.now)
        self.assertFalse(any(
            row["fingerprint"].startswith("provider:")
            for row in incidents
        ))

    def test_unclassified_task_failure_is_not_called_provider_failure(self):
        self._agent_failure(
            summary={"status": "failed"},
            attempt={
                "rc": 1,
                "timed_out": False,
                "error_class": "validation_or_task_failure",
            },
            stdout="task returned no contract result",
        )
        snapshot = self.slo.collect_snapshot(
            state_dir=self.root,
            telegram_database=self.telegram,
            now=self.now,
        )
        self.assertEqual(
            snapshot["recent_failures"][0]["diagnosis_class"],
            "task_failure_unclassified",
        )
        incidents = self.slo.evaluate(snapshot, now=self.now)
        self.assertIn("task:unclassified:B2", {
            row["fingerprint"] for row in incidents
        })
        self.assertFalse(any(
            row["fingerprint"].startswith("provider:")
            for row in incidents
        ))

    def test_actual_timeout_is_classified_as_provider_diagnosis(self):
        self._agent_failure(
            summary={"status": "failed"},
            attempt={
                "rc": 124,
                "timed_out": True,
                "error_class": "provider_timeout",
            },
        )
        snapshot = self.slo.collect_snapshot(
            state_dir=self.root,
            telegram_database=self.telegram,
            now=self.now,
        )
        self.assertEqual(
            snapshot["recent_failures"][0]["diagnosis_class"],
            "provider_timeout",
        )
        incidents = self.slo.evaluate(snapshot, now=self.now)
        self.assertIn("provider:provider_timeout:B2", {
            row["fingerprint"] for row in incidents
        })

    def test_ledger_failure_is_active_only_while_intent_identity_is_missing(self):
        evidence = self.root / "evidence" / "gig-pass-pass-ledger"
        agent = evidence / "agent-B2"
        agent.mkdir(parents=True)
        (agent / "gig-B2-5183000-submitted.intent.json").write_text(
            json.dumps({"request_id": "5183000"})
        )
        (self.root / "pass-failures.jsonl").write_text(json.dumps({
            "ts": self.now - 60,
            "reason": "b2_application_ledger_write_failed",
            "failed_step": "B2",
            "pass_id": "pass-ledger",
            "evidence_dir": str(evidence),
        }) + "\n")
        (self.root / "applied.jsonl").write_text("")

        missing = self.slo.collect_snapshot(
            state_dir=self.root,
            telegram_database=self.telegram,
            now=self.now,
        )
        self.assertEqual(
            missing["recent_failures"][0]["ledger_missing_request_ids"],
            ["5183000"],
        )
        self.assertIn("ledger:application_write_failed:B2", {
            row["fingerprint"] for row in self.slo.evaluate(
                missing, now=self.now
            )
        })

        (self.root / "applied.jsonl").write_text(json.dumps({
            "pass_id": "pass-ledger",
            "requestId": "5183000",
            "status": "applied",
        }) + "\n")
        reconciled = self.slo.collect_snapshot(
            state_dir=self.root,
            telegram_database=self.telegram,
            now=self.now,
        )
        self.assertEqual(
            reconciled["recent_failures"][0]["ledger_missing_request_ids"],
            [],
        )
        self.assertFalse(any(
            row["fingerprint"].startswith("ledger:")
            for row in self.slo.evaluate(reconciled, now=self.now)
        ))

    def test_detected_incidents_are_transactionally_enqueued(self):
        (self.root / "state/lanes/apply.json").write_text(json.dumps({
            "last_attempt_at": self.now - 8000,
            "last_productive_at": self.now - 9000,
            "barren_streak": 0,
        }))
        repair_db = self.root / "repair.sqlite3"
        first = self.slo.evaluate_and_enqueue(
            state_dir=self.root,
            telegram_database=self.telegram,
            repair_database=repair_db,
            now=self.now,
            host_state_dir=self.host_state,
        )
        second = self.slo.evaluate_and_enqueue(
            state_dir=self.root,
            telegram_database=self.telegram,
            repair_database=repair_db,
            now=self.now + 1,
            host_state_dir=self.host_state,
        )
        self.assertEqual(first["incident_count"], 1)
        self.assertEqual(first["incidents"][0]["fingerprint"], "lane:apply:attempt_silence")
        self.assertEqual(second["queue"][0]["occurrence_count"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
