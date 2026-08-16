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
