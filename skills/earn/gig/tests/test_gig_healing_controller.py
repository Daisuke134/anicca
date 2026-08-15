import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "gig"
    / "healing"
    / "controller.py"
)
QUEUE_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "repair_queue.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GigHealingControllerTest(unittest.TestCase):
    def setUp(self):
        self.controller = load(SCRIPT, "gig_healing_controller_under_test")
        self.queue_module = load(QUEUE_SCRIPT, "gig_repair_queue_for_controller_test")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.queue = self.queue_module.RepairQueue(self.root / "control.sqlite3")
        self.audit = self.root / "audit.jsonl"

    def enqueue(self, repair_class="scheduler_restart"):
        return self.queue.enqueue(
            fingerprint="scheduler:missed_hourly_pass",
            repair_class=repair_class,
            evidence={"last_pass_at": 1},
            detected_at=100,
        )

    def test_dispatch_is_not_recovery_until_fresh_state_clears_fingerprint(self):
        self.enqueue()
        snapshots = iter([
            [{"fingerprint": "scheduler:missed_hourly_pass"}],
            [{"fingerprint": "scheduler:missed_hourly_pass"}],
        ])
        result = self.controller.reconcile_once(
            queue=self.queue,
            owner="healer-a",
            uid=501,
            now=120,
            audit_path=self.audit,
            observe_incidents=lambda: next(snapshots),
            dispatcher=lambda repair_class, uid: {
                "status": "dispatched",
                "repair_class": repair_class,
            },
        )
        self.assertEqual(result["status"], "repairing")
        row = self.queue.list_incidents()[0]
        self.assertEqual(row["state"], "queued")
        self.assertEqual(row["attempt_count"], 1)
        self.assertTrue(row["verification"]["fresh_fingerprint_present"])

    def test_fresh_recheck_can_recover_without_repeating_side_effect(self):
        self.enqueue()
        dispatches = []
        result = self.controller.reconcile_once(
            queue=self.queue,
            owner="healer-a",
            uid=501,
            now=120,
            audit_path=self.audit,
            observe_incidents=lambda: [],
            dispatcher=lambda repair_class, uid: dispatches.append(repair_class),
        )
        self.assertEqual(result["status"], "recovered")
        self.assertEqual(dispatches, [])
        row = self.queue.list_incidents()[0]
        self.assertEqual(row["state"], "recovered")
        audit = json.loads(self.audit.read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(audit["kind"], "self_heal_recovery")
        self.assertEqual(audit["state"], "verified")

    def test_unknown_class_is_blocked_without_execution(self):
        self.enqueue(repair_class="new_unknown_repair")
        dispatches = []
        result = self.controller.reconcile_once(
            queue=self.queue,
            owner="healer-a",
            uid=501,
            now=120,
            audit_path=self.audit,
            observe_incidents=lambda: [
                {"fingerprint": "scheduler:missed_hourly_pass"}
            ],
            dispatcher=lambda repair_class, uid: dispatches.append(repair_class),
        )
        self.assertEqual(result["status"], "blocked_unknown_class")
        self.assertEqual(dispatches, [])
        self.assertEqual(self.queue.list_incidents()[0]["state"], "blocked")

    def test_diagnostic_class_runs_read_only_canary_then_blocks_without_repair(self):
        self.enqueue(repair_class="schema_diagnose")
        observations = 0
        diagnoses = []

        def observe():
            nonlocal observations
            observations += 1
            return [{"fingerprint": "scheduler:missed_hourly_pass"}]

        result = self.controller.reconcile_once(
            queue=self.queue,
            owner="healer-a",
            uid=501,
            now=120,
            audit_path=self.audit,
            observe_incidents=observe,
            dispatcher=lambda repair_class, uid, incident: (
                diagnoses.append((repair_class, incident["incident_id"]))
                or {
                    "status": "diagnosed",
                    "repair_class": repair_class,
                    "canary_passed": True,
                }
            ),
        )
        self.assertEqual(result["status"], "diagnosed_blocked")
        self.assertFalse(result["repair_dispatched"])
        self.assertEqual(observations, 1)
        self.assertEqual(diagnoses, [("schema_diagnose", 1)])
        row = self.queue.list_incidents()[0]
        self.assertEqual(row["state"], "blocked")
        self.assertEqual(row["last_action"]["status"], "diagnosed")
        audit = json.loads(self.audit.read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(audit["kind"], "self_heal_diagnosis")
        self.assertEqual(audit["state"], "blocked")

    def test_ledger_reconcile_recovers_only_after_missing_fingerprint_clears(self):
        self.enqueue(repair_class="ledger_reconcile")
        snapshots = iter([
            [{"fingerprint": "scheduler:missed_hourly_pass"}],
            [],
        ])
        dispatched = []
        result = self.controller.reconcile_once(
            queue=self.queue,
            owner="healer-a",
            uid=501,
            now=120,
            audit_path=self.audit,
            observe_incidents=lambda: next(snapshots),
            dispatcher=lambda repair_class, uid, incident: (
                dispatched.append(incident["incident_id"])
                or {
                    "status": "dispatched",
                    "repair_class": repair_class,
                    "recovered": 1,
                }
            ),
        )
        self.assertEqual(result["status"], "recovered")
        self.assertEqual(dispatched, [1])
        self.assertEqual(self.queue.list_incidents()[0]["state"], "recovered")

    def test_third_failed_attempt_is_bounded_and_blocks(self):
        self.enqueue()
        incident = self.queue.claim(owner="seed", now=101, lease_seconds=30)
        self.queue.defer(
            incident["incident_id"],
            owner="seed",
            fencing_token=incident["fencing_token"],
            verification={"fresh_fingerprint_present": True},
            action={"status": "dispatched"},
            next_attempt_at=102,
        )
        incident = self.queue.claim(owner="seed", now=102, lease_seconds=30)
        self.queue.defer(
            incident["incident_id"],
            owner="seed",
            fencing_token=incident["fencing_token"],
            verification={"fresh_fingerprint_present": True},
            action={"status": "dispatched"},
            next_attempt_at=103,
        )
        result = self.controller.reconcile_once(
            queue=self.queue,
            owner="healer-a",
            uid=501,
            now=120,
            audit_path=self.audit,
            observe_incidents=lambda: [
                {"fingerprint": "scheduler:missed_hourly_pass"}
            ],
            dispatcher=lambda repair_class, uid: {
                "status": "dispatched",
                "repair_class": repair_class,
            },
            max_attempts=3,
        )
        self.assertEqual(result["status"], "blocked_attempt_limit")
        self.assertEqual(self.queue.list_incidents()[0]["state"], "blocked")

    def test_batch_drains_stale_incidents_without_any_repair_side_effect(self):
        for index in range(3):
            self.queue.enqueue(
                fingerprint=f"stale:{index}",
                repair_class="scheduler_restart",
                evidence={},
                detected_at=100 + index,
            )
        dispatches = []
        result = self.controller.reconcile_batch(
            queue=self.queue,
            owner="healer-a",
            uid=501,
            now=120,
            audit_path=self.audit,
            observe_incidents=lambda: [],
            dispatcher=lambda repair_class, uid: dispatches.append(repair_class),
            max_incidents=10,
        )
        self.assertEqual(result["status"], "batch_complete")
        self.assertEqual(result["processed"], 3)
        self.assertEqual(result["recovered"], 3)
        self.assertEqual(dispatches, [])
        self.assertEqual(
            [row["state"] for row in self.queue.list_incidents()],
            ["recovered", "recovered", "recovered"],
        )

    def test_batch_stops_after_one_real_repair_dispatch(self):
        for fingerprint in ("scheduler:one", "scheduler:two"):
            self.queue.enqueue(
                fingerprint=fingerprint,
                repair_class="scheduler_restart",
                evidence={},
                detected_at=100,
            )
        dispatches = []
        result = self.controller.reconcile_batch(
            queue=self.queue,
            owner="healer-a",
            uid=501,
            now=120,
            audit_path=self.audit,
            observe_incidents=lambda: [
                {"fingerprint": "scheduler:one"},
                {"fingerprint": "scheduler:two"},
            ],
            dispatcher=lambda repair_class, uid: (
                dispatches.append(repair_class)
                or {"status": "dispatched", "repair_class": repair_class}
            ),
            max_incidents=10,
        )
        self.assertEqual(result["processed"], 1)
        self.assertEqual(dispatches, ["scheduler_restart"])
        self.assertTrue(result["repair_dispatched"])

    def test_blocked_recovery_recheck_is_wired_before_batch_claim(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("requeue_resolved_blocked", source)
        self.assertIn("active_fingerprints", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
