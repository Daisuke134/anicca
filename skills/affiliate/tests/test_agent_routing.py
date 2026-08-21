from __future__ import annotations

import json
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path


CONFIG = Path(__file__).resolve().parents[1] / "config" / "agent-runner.json"
RUNNER = Path(__file__).resolve().parents[1] / "scripts" / "agent_runner.py"


def load_runner_module():
    spec = importlib.util.spec_from_file_location("affiliate_agent_runner", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class AffiliateAgentRoutingTests(unittest.TestCase):
    def test_strategy_and_repair_routes_are_explicit_and_single_candidate(self) -> None:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        strategy = config["task_classes"]["marketing-agent"]
        repair = config["task_classes"]["escalation-agent"]

        self.assertEqual(strategy["route"], "affiliate-terra-high-strategy")
        self.assertTrue(strategy["requires_explicit_escalation"])
        self.assertEqual(
            strategy["candidates"],
            [{"provider": "codex", "model": "gpt-5.6-terra", "effort": "high"}],
        )
        self.assertEqual(repair["route"], "affiliate-sol-one-use-repair")
        self.assertTrue(repair["requires_explicit_escalation"])
        self.assertEqual(
            repair["candidates"],
            [{"provider": "codex", "model": "gpt-5.6-sol", "effort": "high"}],
        )

    def test_evidence_seal_binds_result_and_source_set_and_detects_tampering(self) -> None:
        runner = load_runner_module()
        source_set_sha256 = "a" * 64
        with tempfile.TemporaryDirectory() as temporary:
            evidence_dir = Path(temporary) / "evidence"
            evidence_dir.mkdir(mode=0o700)
            result_path = evidence_dir / "attempt-01.result.json"
            result_path.write_text('{"title":"verified"}\n', encoding="utf-8")
            (evidence_dir / "summary.json").write_text(
                json.dumps({"attempt_count": 1, "result_path": str(result_path)}) + "\n",
                encoding="utf-8",
            )
            (evidence_dir / "attempts.jsonl").write_text('{"attempt":1}\n', encoding="utf-8")

            runner.seal_evidence(evidence_dir, 0, source_set_sha256)
            seal = runner.verify_evidence_seal(evidence_dir, source_set_sha256)

            self.assertEqual(seal["source_set_sha256"], source_set_sha256)
            self.assertEqual(
                seal["result_sha256"], hashlib.sha256(result_path.read_bytes()).hexdigest()
            )
            with self.assertRaises(runner.EvidenceError):
                runner.verify_evidence_seal(evidence_dir, "b" * 64)
            result_path.write_text('{"title":"tampered"}\n', encoding="utf-8")
            with self.assertRaises(runner.EvidenceError):
                runner.verify_evidence_seal(evidence_dir, source_set_sha256)


if __name__ == "__main__":
    unittest.main()
