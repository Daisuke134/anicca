import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from job_search_loop.ledger import Ledger


BASELINE = {
    "version": 1,
    "daily_target": 2,
    "auto_apply_threshold": 75,
    "compensation_floor_jpy": 5_500_000,
}
REPLAY_CASES = [
    {"case_id": "eligible-74", "score": 74, "hard_eligible": True},
    {"case_id": "eligible-82", "score": 82, "hard_eligible": True},
    {"case_id": "hard-reject-99", "score": 99, "hard_eligible": False},
]


class LearningPassTests(unittest.TestCase):
    def _module(self):
        try:
            from job_search_loop import learning
        except ImportError:
            self.fail("job_search_loop.learning is missing")
        return learning

    def _new_driver(self, root: Path):
        learning = self._module()
        ledger = Ledger(root / "ledger.sqlite3")
        driver = learning.LearningDriver(
            ledger,
            baseline_strategy=BASELINE,
            replay_cases=REPLAY_CASES,
        )
        return learning, ledger, driver

    def _seed_outcomes(
        self,
        ledger: Ledger,
        generation_id: str,
        *,
        prefix: str,
        positive: int,
        resolved: int = 10,
    ) -> None:
        for index in range(resolved):
            application_id = ledger.add_attributed_application(
                "Held-out Employer",
                "Applied AI Engineer",
                f"https://jobs.example.com/{prefix}-{index}",
                strategy_generation_id=generation_id,
                source="official_ats",
                query_family="held-out",
                rank_config={"threshold": 75},
                role_family="applied_ai",
                material_variant="engineering_en_v2",
                message_variant="none",
                model_route="codex",
                prompt_sha256="a" * 64,
                material_sha256="b" * 64,
            )
            disposition = "positive" if index < positive else "negative"
            ledger.record_funnel_outcome(
                application_id=application_id,
                funnel_stage="interview",
                disposition=disposition,
                evidence_source="gmail",
                evidence_sha256=hashlib.sha256(
                    f"{prefix}-{index}".encode("utf-8")
                ).hexdigest(),
                occurred_at=f"2026-07-{index + 1:02d}T00:00:00+00:00",
                observed_at="2026-07-30T00:00:00+00:00",
                observation_policy_version=(
                    "interview-window-v1" if disposition == "negative" else None
                ),
            )

    def test_first_pass_bootstraps_one_safe_candidate_and_replay_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            _, ledger, driver = self._new_driver(Path(directory))

            report = driver.run()
            status = driver.status()
            ledger.close()

            self.assertEqual(report["decision"], "inconclusive")
            self.assertEqual(report["reason"], "insufficient_resolved_applications")
            self.assertEqual(status["active_strategy"], BASELINE)
            self.assertEqual(status["candidate_strategy"]["auto_apply_threshold"], 80)
            self.assertEqual(status["changed_field"], "auto_apply_threshold")
            self.assertEqual(status["replay"]["violations"], 0)
            self.assertEqual(status["replay"]["case_count"], 3)
            self.assertRegex(status["replay"]["manifest_sha256"], r"^[a-f0-9]{64}$")

    def test_assignment_is_stable_and_reaches_both_experiment_arms(self):
        with tempfile.TemporaryDirectory() as directory:
            _, ledger, driver = self._new_driver(Path(directory))
            driver.run()

            first = driver.assign("application-key-7")
            second = driver.assign("application-key-7")
            assignments = [driver.assign(f"application-key-{index}") for index in range(64)]
            status = driver.status()
            ledger.close()

            self.assertEqual(first, second)
            self.assertEqual({row["arm"] for row in assignments}, {"baseline", "candidate"})
            valid_generations = {
                status["active_generation_id"],
                status["candidate_generation_id"],
            }
            self.assertTrue(
                all(row["strategy_generation_id"] in valid_generations for row in assignments)
            )

    def test_insufficient_snapshot_is_idempotent_and_keeps_experiment_open(self):
        with tempfile.TemporaryDirectory() as directory:
            _, ledger, driver = self._new_driver(Path(directory))

            first = driver.run()
            second = driver.run()
            decision_count = ledger.connection.execute(
                "SELECT COUNT(*) FROM learning_decisions"
            ).fetchone()[0]
            status = driver.status()
            ledger.close()

            self.assertEqual(second, first)
            self.assertEqual(decision_count, 1)
            self.assertIsNotNone(status["experiment_id"])
            self.assertEqual(status["active_generation_id"], first["baseline_generation_id"])

    def test_promote_atomically_advances_active_pointer_after_separated_intervals(self):
        with tempfile.TemporaryDirectory() as directory:
            _, ledger, driver = self._new_driver(Path(directory))
            initial = driver.run()
            self._seed_outcomes(
                ledger,
                initial["baseline_generation_id"],
                prefix="baseline-promote",
                positive=0,
            )
            self._seed_outcomes(
                ledger,
                initial["candidate_generation_id"],
                prefix="candidate-promote",
                positive=10,
            )

            promoted = driver.run()
            status = driver.status()
            decision = ledger.connection.execute(
                """
                SELECT active_before_generation_id, active_after_generation_id
                FROM learning_decisions
                WHERE decision_id = ?
                """,
                (promoted["decision_id"],),
            ).fetchone()
            ledger.close()

            self.assertEqual(promoted["decision"], "promote")
            self.assertEqual(
                status["active_generation_id"], initial["candidate_generation_id"]
            )
            self.assertIsNone(status["experiment_id"])
            self.assertEqual(
                tuple(decision),
                (
                    initial["baseline_generation_id"],
                    initial["candidate_generation_id"],
                ),
            )

    def test_resolved_overlapping_intervals_close_inconclusive_on_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            _, ledger, driver = self._new_driver(Path(directory))
            initial = driver.run()
            self._seed_outcomes(
                ledger,
                initial["baseline_generation_id"],
                prefix="baseline-overlap",
                positive=5,
            )
            self._seed_outcomes(
                ledger,
                initial["candidate_generation_id"],
                prefix="candidate-overlap",
                positive=6,
            )

            result = driver.run()
            status = driver.status()
            ledger.close()

            self.assertEqual(result["decision"], "inconclusive")
            self.assertEqual(result["reason"], "confidence_intervals_overlap")
            self.assertEqual(
                status["active_generation_id"], initial["baseline_generation_id"]
            )
            self.assertIsNone(status["experiment_id"])

    def test_closed_inconclusive_candidate_is_not_reopened_for_same_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            _, ledger, driver = self._new_driver(Path(directory))
            initial = driver.run()
            self._seed_outcomes(
                ledger,
                initial["baseline_generation_id"],
                prefix="baseline-next",
                positive=5,
            )
            self._seed_outcomes(
                ledger,
                initial["candidate_generation_id"],
                prefix="candidate-next",
                positive=6,
            )
            closed = driver.run()

            next_result = driver.run()
            status = driver.status()
            ledger.close()

            self.assertEqual(closed["reason"], "confidence_intervals_overlap")
            self.assertNotEqual(next_result["experiment_id"], closed["experiment_id"])
            self.assertEqual(status["candidate_strategy"]["auto_apply_threshold"], 85)
            self.assertEqual(
                next_result["reason"], "insufficient_resolved_applications"
            )

    def test_verified_safety_violation_rolls_back_before_sample_threshold(self):
        with tempfile.TemporaryDirectory() as directory:
            _, ledger, driver = self._new_driver(Path(directory))
            initial = driver.run()
            driver.record_candidate_execution(
                outcome="safety_violation",
                evidence_sha256="c" * 64,
                occurred_at="2026-07-30T01:00:00+00:00",
            )

            result = driver.run()
            status = driver.status()
            ledger.close()

            self.assertEqual(result["decision"], "rollback")
            self.assertEqual(result["reason"], "verified_safety_violation")
            self.assertEqual(
                status["active_generation_id"], initial["baseline_generation_id"]
            )
            self.assertIsNone(status["experiment_id"])

    def test_three_consecutive_candidate_failures_roll_back_and_success_resets_streak(self):
        with tempfile.TemporaryDirectory() as directory:
            _, ledger, driver = self._new_driver(Path(directory))
            first_experiment = driver.run()
            for index, outcome in enumerate(
                ("failure", "failure", "success", "failure", "failure")
            ):
                driver.record_candidate_execution(
                    outcome=outcome,
                    evidence_sha256=f"{index + 1:064x}",
                    occurred_at=f"2026-07-30T0{index}:00:00+00:00",
                )
            not_rolled_back = driver.run()
            self.assertEqual(not_rolled_back["decision"], "inconclusive")
            self.assertEqual(driver.status()["candidate_failure_streak"], 2)

            driver.record_candidate_execution(
                outcome="failure",
                evidence_sha256="f" * 64,
                occurred_at="2026-07-30T06:00:00+00:00",
            )
            rolled_back = driver.run()
            status = driver.status()
            ledger.close()

            self.assertEqual(rolled_back["decision"], "rollback")
            self.assertEqual(
                rolled_back["reason"], "three_consecutive_candidate_failures"
            )
            self.assertEqual(
                status["active_generation_id"],
                first_experiment["baseline_generation_id"],
            )
            self.assertIsNone(status["experiment_id"])

    def test_decision_and_execution_receipts_are_database_immutable(self):
        with tempfile.TemporaryDirectory() as directory:
            _, ledger, driver = self._new_driver(Path(directory))
            report = driver.run()
            driver.record_candidate_execution(
                outcome="success",
                evidence_sha256="d" * 64,
                occurred_at="2026-07-30T01:00:00+00:00",
            )
            event_id = ledger.connection.execute(
                "SELECT event_id FROM learning_execution_events"
            ).fetchone()[0]

            with self.assertRaises(sqlite3.IntegrityError):
                ledger.connection.execute(
                    "UPDATE learning_decisions SET decision='promote' WHERE decision_id=?",
                    (report["decision_id"],),
                )
            with self.assertRaises(sqlite3.IntegrityError):
                ledger.connection.execute(
                    "DELETE FROM learning_execution_events WHERE event_id=?",
                    (event_id,),
                )
            ledger.close()

    def test_stale_active_pointer_fences_decision_instead_of_overwriting_race(self):
        with tempfile.TemporaryDirectory() as directory:
            _, ledger, driver = self._new_driver(Path(directory))
            initial = driver.run()
            driver.record_candidate_execution(
                outcome="failure",
                evidence_sha256="e" * 64,
                occurred_at="2026-07-30T01:00:00+00:00",
            )
            ledger.connection.execute(
                f"""
                CREATE TRIGGER simulate_learning_pointer_race
                BEFORE INSERT ON learning_decisions
                BEGIN
                    UPDATE strategy_learning_control
                    SET active_generation_id =
                        '{initial["candidate_generation_id"]}'
                    WHERE scope = 'default';
                END
                """
            )

            with self.assertRaisesRegex(RuntimeError, "changed during decision"):
                driver.run()
            control = ledger.connection.execute(
                """
                SELECT active_generation_id, experiment_id
                FROM strategy_learning_control
                WHERE scope = 'default'
                """
            ).fetchone()
            ledger.close()

            self.assertEqual(
                tuple(control),
                (
                    initial["baseline_generation_id"],
                    initial["experiment_id"],
                ),
            )

    def test_learning_report_delivery_is_content_addressed_and_at_most_once(self):
        learning = self._module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, ledger, driver = self._new_driver(root)
            report = driver.run()
            ledger.close()
            executable = root / "fake-openclaw"
            executable.write_text(
                """#!/usr/bin/env python3
import json
import pathlib

counter = pathlib.Path(__file__).with_suffix(".count")
count = int(counter.read_text()) if counter.exists() else 0
counter.write_text(str(count + 1))
print(json.dumps({"messageId": "learning-901"}))
""",
                encoding="utf-8",
            )
            executable.chmod(0o700)

            first = learning.deliver_learning_report(
                report,
                database=root / "telegram.sqlite3",
                executable=str(executable),
            )
            second = learning.deliver_learning_report(
                report,
                database=root / "telegram.sqlite3",
                executable=str(executable),
            )

            self.assertEqual(first["status"], "sent")
            self.assertEqual(first["message_id"], "learning-901")
            self.assertEqual(second, first)
            self.assertEqual(executable.with_suffix(".count").read_text(), "1")
            self.assertNotIn("Held-out Employer", json.dumps(report))

    def test_resident_script_writes_private_receipt_and_reuses_telegram_ack(self):
        app_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / "fake-openclaw"
            executable.write_text(
                """#!/usr/bin/env python3
import json
import pathlib

counter = pathlib.Path(__file__).with_suffix(".count")
count = int(counter.read_text()) if counter.exists() else 0
counter.write_text(str(count + 1))
print(json.dumps({"messageId": "learning-script-902"}))
""",
                encoding="utf-8",
            )
            executable.chmod(0o700)
            env = {
                **os.environ,
                "HOME": str(root / "home"),
                "XDG_STATE_HOME": str(root / "state"),
                "JOB_SEARCH_STATE_ROOT": str(root / "job-state"),
                "JOB_SEARCH_PYTHON": sys.executable,
                "JOB_SEARCH_OPENCLAW": str(executable),
            }

            first = subprocess.run(
                ["/bin/zsh", str(app_root / "scripts" / "run-learning.sh")],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )
            second = subprocess.run(
                ["/bin/zsh", str(app_root / "scripts" / "run-learning.sh")],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            reports = sorted(
                (root / "job-state" / "evidence").glob(
                    "learning-*/learning-decision.json"
                )
            )
            self.assertEqual(len(reports), 2)
            self.assertTrue(all(path.stat().st_mode & 0o777 == 0o600 for path in reports))
            first_report = json.loads(reports[0].read_text(encoding="utf-8"))
            second_report = json.loads(reports[1].read_text(encoding="utf-8"))
            self.assertEqual(first_report["decision_id"], second_report["decision_id"])
            self.assertEqual(first_report["decision"], "inconclusive")
            self.assertEqual(executable.with_suffix(".count").read_text(), "1")


if __name__ == "__main__":
    unittest.main()
