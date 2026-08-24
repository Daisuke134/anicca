from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "funnel_decision.py"
sys.path.insert(0, str(SCRIPT.parent))


class FunnelDecisionTests(unittest.TestCase):
    def test_distribution_plan_gets_one_model_route(self):
        spec = importlib.util.spec_from_file_location("affiliate_funnel_decision", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            plan = {
                "state": "READY", "plan_id": "a" * 64,
                "control_placement_id": "caption-en-1",
                "decision_action": "Use one additional relevant channel.",
                "live_surfaces": ["devto", "substack", "x"],
                "official_success_metric": "At least 100 exact impressions.",
            }
            module._write(state / "money-funnel" / "latest.json", {
                "transition_id": "b" * 64, "impressions": {"count": 37, "state": "EXACT"},
                "transactions": {"count": 0, "state": "OBSERVED"},
            })
            module._write(state / "x-growth" / "latest-post-metrics.json", {
                "placement_id": "caption-en-1", "post_url": "https://x.com/a/status/1",
                "impressions": {"count": 1, "state": "EXACT"},
            })
            calls = []

            def runner(_skill_root, _state, context, _sha, _run_id):
                calls.append(context)
                return {
                    "target": "x_relevant_external_quote",
                    "reason": "Self quotes have low measured reach.",
                    "evidence": ["three owned surfaces are already live"],
                    "result_sha256": "c" * 64,
                    "execution": {"selected_model": "gpt-5.6-terra"},
                }

            first = module.advance_distribution_route(
                Path(directory), state, plan, "run-1", runner=runner,
            )
            replay = module.advance_distribution_route(
                Path(directory), state, plan, "run-2", runner=runner,
            )

            self.assertEqual(first["target"], "x_relevant_external_quote")
            self.assertTrue(first["changed"])
            self.assertFalse(replay["changed"])
            self.assertEqual(len(calls), 1)

    def test_one_funnel_transition_gets_one_model_decision(self):
        self.assertTrue(SCRIPT.is_file(), f"missing decision owner: {SCRIPT}")
        spec = importlib.util.spec_from_file_location("affiliate_funnel_decision", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            funnel = {
                "schema_version": 1,
                "receipt_type": "AFFILIATE_MONEY_FUNNEL_ROW",
                "transition_id": "a" * 64,
                "placement_id": "caption-en-1",
                "impressions": {"count": 6, "state": "EXACT"},
                "owned_entries": {"count": None, "state": "UNKNOWN_NOT_IN_COHORT"},
                "cta_clicks": {"count": None, "state": "UNKNOWN_NOT_IN_COHORT"},
                "provider_clicks": {"post_distribution_count": None,
                                    "post_distribution_state": "WAITING_FOR_POST_PROVIDER_READBACK"},
                "transactions": {"count": 0, "state": "OBSERVED"},
                "approved_or_paid_money_state": "NO_APPROVED_OR_PAID",
                "cost": {"state": "UNKNOWN"},
            }
            module._write(state / "money-funnel" / "latest.json", funnel)
            calls = []

            def runner(_skill_root, _state, context, _context_sha, _run_id):
                calls.append(context)
                return {
                    "bottleneck": "reach",
                    "exposure_assessment": "insufficient",
                    "selected_variable": "distribution_mix",
                    "hypothesis": "More exact qualified reach is needed before conversion judgment.",
                    "action": "Increase relevant growth-to-owned distribution for this placement.",
                    "official_success_metric": "Exact X impressions increase from the sealed baseline.",
                    "evidence": ["impressions=6", "owned_entries=UNKNOWN"],
                    "result_sha256": "b" * 64,
                    "execution": {"selected_model": "gpt-5.6-terra"},
                }

            first = module.advance(Path(directory), state, "run-1", runner=runner)
            second = module.advance(Path(directory), state, "run-2", runner=runner)

            self.assertEqual(first["state"], "READY")
            self.assertTrue(first["changed"])
            self.assertEqual(second["state"], "ALREADY_DECIDED")
            self.assertFalse(second["changed"])
            self.assertEqual(len(calls), 1)
            self.assertEqual(first["source_funnel_transition_id"], funnel["transition_id"])
            self.assertEqual(first["selected_variable"], "distribution_mix")


if __name__ == "__main__":
    unittest.main()
