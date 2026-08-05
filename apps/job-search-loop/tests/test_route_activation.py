import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from job_search_loop.route_activation import RouteActivationError, validate_route_gate


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class RouteActivationTests(unittest.TestCase):
    def _fixture(self, root: Path):
        release = root / "releases" / "abc123"
        evidence = root / "route-replays" / "abc123"
        config = {
            "task_classes": {
                "repeatable-agent": {"candidates": [{"model": "gpt-5.6-luna", "effort": "medium"}]},
                "composition-agent": {"candidates": [{"model": "gpt-5.6-terra", "effort": "medium"}]},
                "browser-lane-agent": {"candidates": [{"model": "gpt-5.6-terra", "effort": "medium"}]},
                "job-search-terra-high": {"requires_explicit_escalation": True, "candidates": [{"model": "gpt-5.6-terra", "effort": "high"}]},
            }
        }
        snapshot = {"version": 1, "cases": [{"case_id": "one"}]}
        (release / "runtime" / "agent-runner").mkdir(parents=True)
        (release / "apps" / "job-search-loop" / "config").mkdir(parents=True)
        (release / "runtime" / "agent-runner" / "config.json").write_text(json.dumps(config))
        (release / "apps" / "job-search-loop" / "config" / "model-route-replay.v1.json").write_text(json.dumps(snapshot))
        evidence.mkdir(parents=True)
        receipt = {
            "version": 1, "status": "pass", "snapshot_sha256": digest(snapshot),
            "sample_count": {"luna": 3, "terra": 3},
            "quality": {"luna": 1.0, "terra": 1.0},
            "evidence_not_weakened": True, "luna_cheaper": True, "luna_faster": True,
        }
        receipt["receipt_sha256"] = digest(receipt)
        (evidence / "route-replay-receipt.json").write_text(json.dumps(receipt))
        for route, model, effort in (("luna", "gpt-5.6-luna", "medium"), ("terra", "gpt-5.6-terra", "medium")):
            for trial in range(1, 4):
                lane = evidence / f"{route}-{trial}"
                lane.mkdir()
                (lane / "summary.json").write_text(json.dumps({"status": "success", "selected_model": model, "selected_effort": effort}))
                (lane / "attempts.jsonl").write_text(json.dumps({"rc": 0, "schema_valid": True, "model": model, "effort": effort}) + "\n")
        return release, evidence

    def test_valid_gate_binds_release_receipt_and_six_attempts(self):
        with tempfile.TemporaryDirectory() as directory:
            release, evidence = self._fixture(Path(directory))
            gate = validate_route_gate(release, evidence, expected_commit="abc123")
            self.assertEqual(gate["status"], "approved")
            self.assertEqual(gate["attempt_count"], 6)

    def test_receipt_copied_under_another_commit_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            release, evidence = self._fixture(Path(directory))
            with self.assertRaisesRegex(RouteActivationError, "commit"):
                validate_route_gate(release, evidence, expected_commit="different")

    def test_any_non_schema_valid_attempt_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            release, evidence = self._fixture(Path(directory))
            attempt = evidence / "luna-2" / "attempts.jsonl"
            attempt.write_text(json.dumps({"rc": 0, "schema_valid": False, "model": "gpt-5.6-luna", "effort": "medium"}) + "\n")
            with self.assertRaisesRegex(RouteActivationError, "attempt"):
                validate_route_gate(release, evidence, expected_commit="abc123")


if __name__ == "__main__":
    unittest.main()
