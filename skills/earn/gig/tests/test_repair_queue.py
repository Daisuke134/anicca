import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "repair_queue.py"


def load():
    spec = importlib.util.spec_from_file_location("repair_queue_under_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load repair_queue")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RepairQueueTest(unittest.TestCase):
    def setUp(self):
        self.module = load()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.queue = self.module.RepairQueue(Path(self.temp.name) / "gig.sqlite3")

    def enqueue(self, fingerprint="scheduler:missed_hourly_pass", detected_at=100):
        return self.queue.enqueue(
            fingerprint=fingerprint,
            repair_class="scheduler_restart",
            evidence={"last_pass_at": 1},
            detected_at=detected_at,
        )

    def test_duplicate_open_incident_is_coalesced(self):
        first = self.enqueue()
        second = self.enqueue(detected_at=110)
        self.assertEqual(first["incident_id"], second["incident_id"])
        self.assertEqual(second["occurrence_count"], 2)
        self.assertEqual(len(self.queue.list_incidents()), 1)

    def test_distinct_fingerprints_remain_independent(self):
        self.enqueue()
        self.enqueue("lane:apply:attempt_silence")
        self.assertEqual(len(self.queue.list_incidents()), 2)

    def test_claim_is_transactional_and_fenced(self):
        self.enqueue()
        claimed = self.queue.claim(owner="healer-a", now=120, lease_seconds=30)
        self.assertEqual(claimed["state"], "claimed")
        self.assertEqual(claimed["fencing_token"], 1)
        self.assertIsNone(self.queue.claim(owner="healer-b", now=121, lease_seconds=30))

    def test_expired_claim_can_be_reclaimed_with_a_new_fence(self):
        self.enqueue()
        first = self.queue.claim(owner="healer-a", now=120, lease_seconds=10)
        second = self.queue.claim(owner="healer-b", now=131, lease_seconds=10)
        self.assertEqual(second["incident_id"], first["incident_id"])
        self.assertEqual(second["fencing_token"], 2)
        self.assertEqual(second["owner"], "healer-b")

    def test_healer_can_claim_only_allowlisted_repair_classes(self):
        self.queue.enqueue(
            fingerprint="lane:reply:productive_silence",
            repair_class="lane_diagnose",
            evidence={},
            detected_at=100,
        )
        self.enqueue(detected_at=101)
        claimed = self.queue.claim(
            owner="healer-a",
            now=120,
            lease_seconds=30,
            allowed_classes={"scheduler_restart", "browser_restart"},
        )
        self.assertEqual(claimed["repair_class"], "scheduler_restart")

    def test_recovery_requires_current_owner_and_records_verification(self):
        self.enqueue()
        claimed = self.queue.claim(owner="healer-a", now=120, lease_seconds=30)
        with self.assertRaises(self.module.LostLease):
            self.queue.recover(
                claimed["incident_id"],
                owner="healer-b",
                fencing_token=claimed["fencing_token"],
                verification={"canary": "pass"},
                recovered_at=130,
            )
        recovered = self.queue.recover(
            claimed["incident_id"],
            owner="healer-a",
            fencing_token=claimed["fencing_token"],
            verification={"canary": "pass"},
            recovered_at=130,
        )
        self.assertEqual(recovered["state"], "recovered")
        self.assertEqual(recovered["verification"], {"canary": "pass"})

    def test_same_fingerprint_can_open_again_after_recovery(self):
        first = self.enqueue()
        claimed = self.queue.claim(owner="healer-a", now=120, lease_seconds=30)
        self.queue.recover(
            claimed["incident_id"],
            owner="healer-a",
            fencing_token=claimed["fencing_token"],
            verification={"canary": "pass"},
            recovered_at=130,
        )
        second = self.enqueue(detected_at=200)
        self.assertNotEqual(first["incident_id"], second["incident_id"])

    def test_deferred_repair_is_rate_limited_and_keeps_attempt_evidence(self):
        self.enqueue()
        claimed = self.queue.claim(owner="healer-a", now=120, lease_seconds=30)
        deferred = self.queue.defer(
            claimed["incident_id"],
            owner="healer-a",
            fencing_token=claimed["fencing_token"],
            verification={"fresh_fingerprint_present": True},
            action={"status": "dispatched", "repair_class": "scheduler_restart"},
            next_attempt_at=180,
        )
        self.assertEqual(deferred["state"], "queued")
        self.assertEqual(deferred["attempt_count"], 1)
        self.assertEqual(deferred["next_attempt_at"], 180)
        self.assertEqual(deferred["last_action"]["status"], "dispatched")
        self.assertIsNone(
            self.queue.claim(owner="healer-b", now=179, lease_seconds=30)
        )
        reclaimed = self.queue.claim(
            owner="healer-b", now=180, lease_seconds=30
        )
        self.assertEqual(reclaimed["incident_id"], claimed["incident_id"])
        self.assertEqual(reclaimed["fencing_token"], 2)

    def test_blocked_repair_is_not_claimed_again(self):
        self.enqueue()
        claimed = self.queue.claim(owner="healer-a", now=120, lease_seconds=30)
        blocked = self.queue.block(
            claimed["incident_id"],
            owner="healer-a",
            fencing_token=claimed["fencing_token"],
            verification={"reason": "unknown_class_requires_canary"},
            blocked_at=125,
        )
        self.assertEqual(blocked["state"], "blocked")
        self.assertEqual(blocked["verification"]["reason"], "unknown_class_requires_canary")
        self.assertIsNone(
            self.queue.claim(owner="healer-b", now=200, lease_seconds=30)
        )

    def test_blocked_incident_requeues_only_after_fingerprint_disappears(self):
        first = self.enqueue()
        claimed = self.queue.claim(owner="healer-a", now=120, lease_seconds=30)
        self.queue.block(
            claimed["incident_id"],
            owner="healer-a",
            fencing_token=claimed["fencing_token"],
            verification={"reason": "patch_handoff"},
            blocked_at=125,
        )
        unchanged = self.queue.requeue_resolved_blocked(
            active_fingerprints={first["fingerprint"]},
            now=200,
        )
        self.assertEqual(unchanged, [])
        self.assertEqual(self.queue.list_incidents()[0]["state"], "blocked")

        requeued = self.queue.requeue_resolved_blocked(
            active_fingerprints=set(),
            now=201,
        )
        self.assertEqual([row["incident_id"] for row in requeued], [1])
        self.assertEqual(requeued[0]["state"], "queued")
        self.assertEqual(
            requeued[0]["verification"]["reason"],
            "blocked_fingerprint_absent_recheck",
        )
        self.assertIsNotNone(
            self.queue.claim(owner="healer-b", now=201, lease_seconds=30)
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
