import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "acquisition_decision.py"
SPEC = importlib.util.spec_from_file_location("affiliate_acquisition_decision", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class AcquisitionDecisionTest(unittest.TestCase):
    def test_retry_budget_scope_is_unique_per_scheduler_run(self):
        baseline = "a" * 64
        self.assertEqual(
            MODULE._budget_scope(baseline, "run-one"),
            "affiliate-acquisition-aaaaaaaaaaaaaaaa-run-one",
        )
        self.assertNotEqual(
            MODULE._budget_scope(baseline, "run-one"),
            MODULE._budget_scope(baseline, "run-two"),
        )

    def test_budget_blocked_summary_is_not_reported_as_runner_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            evidence = Path(directory)
            (evidence / "summary.json").write_text(json.dumps({
                "status": "budget_blocked",
                "budget": {"reason": "pass_token_budget_exceeded"},
            }))
            self.assertEqual(
                MODULE._runner_failure_type(evidence, 1), "BUDGET_BLOCKED"
            )

    def test_local_owner_passes_scheduler_run_id(self):
        local_loop = (SCRIPT.parent / "local_loop.py").read_text()
        self.assertIn(
            "advance_acquisition_decision(\n                Path(__file__).resolve().parent.parent, state, run_id",
            local_loop,
        )

    def test_context_binds_hash_valid_placement_economics(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            baseline = {"plan_id": "alpha-en", "placement_id": "alpha-en-1"}
            core = {
                "schema_version": 1,
                "receipt_type": "AFFILIATE_PLACEMENT_LEDGER",
                "observed_at": "observed",
                "placements": [{
                    "placement_id": "alpha-en-1",
                    "cost": {"actual_cash_state": "UNKNOWN"},
                    "unit_economics": {"actual_net_profit_state": "UNKNOWN_COST"},
                }],
            }
            core["ledger_sha256"] = hashlib.sha256(json.dumps(
                core, sort_keys=True, separators=(",", ":")
            ).encode()).hexdigest()
            (state / "placement-ledger.json").write_text(json.dumps(core))

            context, ledger_sha256 = MODULE._context(state, baseline)

            self.assertEqual(ledger_sha256, core["ledger_sha256"])
            self.assertEqual(context["placement_economics"]["state"], "OBSERVED")
            self.assertEqual(
                context["placement_economics"]["placements"][0]["placement_id"],
                "alpha-en-1",
            )


if __name__ == "__main__":
    unittest.main()
