from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SKILL_ROOT / "scripts" / "guarded_dispatch.py"


class GuardedDispatchTests(unittest.TestCase):
    def load_module(self):
        self.assertTrue(MODULE_PATH.is_file(), f"missing guarded dispatcher: {MODULE_PATH}")
        spec = importlib.util.spec_from_file_location("guarded_dispatch", MODULE_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_model_cannot_invoke_external_command_even_with_forged_gates(self) -> None:
        module = self.load_module()
        called = []
        result = module.dispatch(
            "x post publish",
            caller="model",
            state_root=Path("/does/not/matter"),
            claim_id="forged",
            policy_path=Path("/forged"),
            readback_command="x inspect",
            operation=lambda: called.append(True),
        )
        self.assertEqual(result["state"], "DIRECT_EFFECT_REJECTED")
        self.assertEqual(called, [])

    def test_owner_requires_all_durable_gates_before_one_dispatch(self) -> None:
        module = self.load_module()
        with tempfile.TemporaryDirectory() as root:
            state = Path(root)
            jobs = state / "jobs"
            jobs.mkdir()
            claim_id = "a" * 64
            (jobs / f"{claim_id}.json").write_text(json.dumps({
                "job_id": claim_id,
                "state": "EFFECT_STARTED",
                "kind": "x-post",
                "target": "placement-1",
            }))
            policy = state / "policy.json"
            policy.write_text(json.dumps({"decision": "PASS"}))
            (state / "cost-ledger.jsonl").write_text(json.dumps({
                "cost_id": "cost-1",
                "cost_basis": "actual_billed",
                "currency": "USD",
                "amount_minor": 0,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            }) + "\n")

            calls = []
            admitted = module.dispatch(
                "x post publish",
                caller="ai.anicca.affiliate-loop",
                state_root=state,
                claim_id=claim_id,
                policy_path=policy,
                readback_command="x inspect",
                operation=lambda: calls.append(True) or {
                    "state": "X_LIVE",
                    "effect_id": claim_id,
                    "readback_status": "EXACT",
                },
            )
            self.assertEqual(admitted["state"], "X_LIVE")
            self.assertEqual(calls, [True])

            for broken in ("claim", "policy", "cost", "quarantine", "readback"):
                calls.clear()
                claim = claim_id
                readback = "x inspect"
                policy.write_text(json.dumps({"decision": "PASS"}))
                (state / "cost-ledger.jsonl").write_text(json.dumps({
                    "cost_id": "cost-1",
                    "cost_basis": "actual_billed",
                    "currency": "USD",
                    "amount_minor": 0,
                    "occurred_at": datetime.now(timezone.utc).isoformat(),
                }) + "\n")
                (state / "tool-attempt-receipts.jsonl").unlink(missing_ok=True)
                if broken == "claim":
                    claim = "b" * 64
                elif broken == "policy":
                    policy.write_text(json.dumps({"decision": "FAIL"}))
                elif broken == "cost":
                    (state / "cost-ledger.jsonl").write_text(json.dumps({
                        "cost_id": "cost-2", "cost_basis": "actual_billed",
                        "currency": "USD", "amount_minor": 500,
                        "occurred_at": datetime.now(timezone.utc).isoformat(),
                    }) + "\n")
                elif broken == "quarantine":
                    rows = [json.dumps({
                        "tool": "x post publish", "effect_class": "EXTERNAL_WRITE",
                        "outcome": "FAILED", "failure_type": "ProviderError",
                    }) for _ in range(3)]
                    (state / "tool-attempt-receipts.jsonl").write_text("\n".join(rows) + "\n")
                else:
                    readback = "x post publish"
                rejected = module.dispatch(
                    "x post publish",
                    caller="ai.anicca.affiliate-loop",
                    state_root=state,
                    claim_id=claim,
                    policy_path=policy,
                    readback_command=readback,
                    operation=lambda: calls.append(True),
                )
                self.assertEqual(rejected["state"], "DISPATCH_REJECTED", broken)
                self.assertEqual(calls, [], broken)


if __name__ == "__main__":
    unittest.main()
