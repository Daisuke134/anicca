import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from job_search_loop.route_replay import ReplayError, evaluate_route_replay, measured_result


SNAPSHOT = {
    "version": 1,
    "cases": [
        {"case_id": "eligible", "expected": {"hard_eligible": True}, "required_evidence": ["Tokyo", "JPY 12,000,000"]},
        {"case_id": "low-pay", "expected": {"hard_eligible": False}, "required_evidence": ["JPY 6,000,000"]},
    ],
}


def result(latency, cost):
    return {
        "snapshot_sha256": "",
        "results": [
            {"case_id": "eligible", "hard_eligible": True, "evidence_spans": ["Tokyo", "JPY 12,000,000"]},
            {"case_id": "low-pay", "hard_eligible": False, "evidence_spans": ["JPY 6,000,000"]},
        ],
        "latency_seconds": latency,
        "cost_usd": cost,
    }


class RouteReplayTests(unittest.TestCase):
    def test_route_replay_shell_uses_braced_scope_ids(self):
        script = (Path(__file__).parents[1] / "scripts" / "run-route-replay.sh").read_text()
        self.assertIn('${RUN_ID}:luna', script)
        self.assertIn('${RUN_ID}:terra', script)
        self.assertNotIn('$RUN_ID:luna', script)
        self.assertNotIn('$RUN_ID:terra', script)

    def test_equal_quality_and_evidence_with_faster_cheaper_luna_passes(self):
        raw = json.dumps(SNAPSHOT, sort_keys=True, separators=(",", ":")).encode()
        digest = hashlib.sha256(raw).hexdigest()
        luna, terra = result(2.0, 0.01), result(5.0, 0.03)
        luna["snapshot_sha256"] = terra["snapshot_sha256"] = digest
        receipt = evaluate_route_replay(SNAPSHOT, {"luna": luna, "terra": terra})
        self.assertEqual(receipt["status"], "pass")
        self.assertEqual(receipt["quality"], {"luna": 1.0, "terra": 1.0})
        self.assertTrue(receipt["evidence_not_weakened"])

    def test_missing_evidence_fails_gate(self):
        raw = json.dumps(SNAPSHOT, sort_keys=True, separators=(",", ":")).encode()
        digest = hashlib.sha256(raw).hexdigest()
        luna, terra = result(2.0, 0.01), result(5.0, 0.03)
        luna["snapshot_sha256"] = terra["snapshot_sha256"] = digest
        luna["results"][0]["evidence_spans"] = ["Tokyo"]
        self.assertEqual(evaluate_route_replay(SNAPSHOT, {"luna": luna, "terra": terra})["status"], "fail")

    def test_snapshot_hash_mismatch_is_rejected(self):
        luna, terra = result(2.0, 0.01), result(5.0, 0.03)
        with self.assertRaisesRegex(ReplayError, "snapshot"):
            evaluate_route_replay(SNAPSHOT, {"luna": luna, "terra": terra})

    def test_metrics_come_from_runner_attempt_not_model_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = root / "result.json"
            model.write_text(json.dumps({"snapshot_sha256": "a" * 64, "results": [], "cost_usd": 999}))
            attempts = root / "attempts.jsonl"
            attempts.write_text(json.dumps({
                "rc": 0, "schema_valid": True, "duration_ms": 1250,
                "usage": {"provider_cost_usd": 0.02},
            }) + "\n")
            measured = measured_result(model, attempts)
            self.assertEqual(measured["latency_seconds"], 1.25)
            self.assertEqual(measured["cost_usd"], 0.02)


if __name__ == "__main__":
    unittest.main()
