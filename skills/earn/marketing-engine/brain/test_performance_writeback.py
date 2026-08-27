from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("performance_writeback.py")
SPEC = importlib.util.spec_from_file_location("performance_writeback", MODULE_PATH)
assert SPEC and SPEC.loader
pw = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = pw
SPEC.loader.exec_module(pw)


def snapshot(index: int, *, age_hours: int = 30, click: int | None = 0,
             views: int | None = 100):
    published = "2026-08-01T00:00:00Z"
    observed = "2026-08-02T06:00:00Z" if age_hours >= 24 else "2026-08-01T01:00:00Z"
    results = []
    for name in pw.METRIC_ORDER:
        value = click if name == "qualified_clicks" else views if name == "views" else None
        results.append({
            "metric_name": name,
            "status": "observed" if value is not None else "unknown",
            "value": value,
            "attribution_class": "deterministic" if value is not None else "unknown",
        })
    return {
        "schema_version": "marketing.experiment-attribution.v1",
        "attribution_id": f"attribution.{index:024x}",
        "experiment_id": f"experiment.{index:024x}",
        "hook_id": f"hook.{index}", "renderer_id": "watercolor-monk",
        "product_id": "ebook-ja", "account_id": "tiktok.obou_anicca",
        "published_at": published, "observed_at": observed, "results": results,
    }


class PerformanceWritebackTest(unittest.TestCase):
    def test_young_or_small_cohort_emits_no_mutation(self):
        decision = pw.build_decision(
            snapshots=[snapshot(1, age_hours=1)], observed_at="2026-08-01T01:00:00Z",
            product_id="ebook-ja", platform="tiktok", renderer_id="watercolor-monk")
        self.assertEqual(decision["status"], "insufficient_data")
        self.assertEqual(decision["eligible_experiments"], 0)
        self.assertEqual(decision["mutations"], [])
        decision = pw.build_decision(
            snapshots=[snapshot(i) for i in range(9)], observed_at="2026-08-02T06:00:00Z",
            product_id="ebook-ja", platform="tiktok", renderer_id="watercolor-monk")
        self.assertEqual(decision["status"], "insufficient_data")
        self.assertEqual(decision["eligible_experiments"], 9)
        self.assertEqual(decision["winners"], [])
        self.assertEqual(decision["losers"], [])

    def test_ten_mature_posts_use_deepest_common_signal_and_top_bottom_twenty(self):
        rows = [snapshot(i, click=i, views=1000 - i) for i in range(10)]
        decision = pw.build_decision(
            snapshots=rows, observed_at="2026-08-02T06:00:00Z",
            product_id="ebook-ja", platform="tiktok", renderer_id="watercolor-monk")
        self.assertEqual(decision["status"], "scored")
        self.assertEqual(decision["reward_metric"], "qualified_clicks")
        self.assertEqual(len(decision["winners"]), 2)
        self.assertEqual(len(decision["losers"]), 2)
        self.assertEqual({row["value"] for row in decision["winners"]}, {8, 9})
        self.assertEqual({row["value"] for row in decision["losers"]}, {0, 1})

    def test_missing_click_falls_back_to_views_for_entire_cohort(self):
        rows = [snapshot(i, click=i, views=i + 10) for i in range(10)]
        rows[0]["results"] = [
            ({**result, "status": "unknown", "value": None,
              "attribution_class": "unknown"}
             if result["metric_name"] == "qualified_clicks" else result)
            for result in rows[0]["results"]
        ]
        decision = pw.build_decision(
            snapshots=rows, observed_at="2026-08-02T06:00:00Z",
            product_id="ebook-ja", platform="tiktok", renderer_id="watercolor-monk")
        self.assertEqual(decision["reward_metric"], "views")

    def test_append_is_idempotent_and_conflict_fails(self):
        decision = pw.build_decision(
            snapshots=[snapshot(1)], observed_at="2026-08-02T06:00:00Z",
            product_id="ebook-ja", platform="tiktok", renderer_id="watercolor-monk")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hook-perf.jsonl"
            self.assertTrue(pw.append_decision(path, decision))
            self.assertFalse(pw.append_decision(path, decision))
            changed = json.loads(json.dumps(decision))
            changed["reason"] = "changed"
            with self.assertRaisesRegex(ValueError, "conflicting writeback replay"):
                pw.append_decision(path, changed)

    def test_hook_ewma_updates_and_loser_needs_three_observations(self):
        decision = pw.build_decision(
            snapshots=[snapshot(i, click=i) for i in range(10)],
            observed_at="2026-08-02T06:00:00Z", product_id="ebook-ja",
            platform="tiktok", renderer_id="watercolor-monk")
        hooks = []
        for i in range(10):
            hooks.append({"id": f"hook.{i}", "status": "active",
                          "ewma_score": 0.5, "observations": 1})
        updated, receipts = pw.apply_hook_updates(decision, hooks)
        by_id = {row["id"]: row for row in updated}
        self.assertAlmostEqual(by_id["hook.9"]["ewma_score"], 0.65)
        self.assertEqual(by_id["hook.9"]["observations"], 2)
        self.assertEqual(by_id["hook.0"]["status"], "active")
        self.assertIn("minimum_three_observations", {
            row.get("retirement_blocked_reason") for row in receipts})

    def test_third_real_loss_can_retire_without_breaking_exploration_floor(self):
        decision = pw.build_decision(
            snapshots=[snapshot(i, click=i) for i in range(10)],
            observed_at="2026-08-02T06:00:00Z", product_id="ebook-ja",
            platform="tiktok", renderer_id="watercolor-monk")
        hooks = [{"id": f"hook.{i}", "status": "active", "ewma_score": 0.2,
                  "observations": 2} for i in range(10)]
        updated, _ = pw.apply_hook_updates(decision, hooks)
        by_id = {row["id"]: row for row in updated}
        self.assertEqual(by_id["hook.0"]["status"], "retired")
        self.assertEqual(by_id["hook.1"]["status"], "retired")
        self.assertGreaterEqual(sum(row["status"] == "active" for row in updated), 2)

    def test_insufficient_decision_never_changes_hooks(self):
        decision = pw.build_decision(
            snapshots=[snapshot(1, age_hours=1)], observed_at="2026-08-01T01:00:00Z",
            product_id="ebook-ja", platform="tiktok", renderer_id="watercolor-monk")
        hooks = [{"id": "hook.1", "status": "active", "ewma_score": None,
                  "observations": 0}]
        updated, receipts = pw.apply_hook_updates(decision, hooks)
        self.assertEqual(updated, hooks)
        self.assertEqual(receipts, [])

    def test_tactic_requires_exact_plan_mapping_but_renderer_can_be_observed(self):
        decision = pw.build_decision(
            snapshots=[snapshot(i, click=i) for i in range(10)],
            observed_at="2026-08-02T06:00:00Z", product_id="ebook-ja",
            platform="tiktok", renderer_id="watercolor-monk")
        result = pw.build_entity_performance(decision, experiment_plans=[])
        self.assertEqual(result["tactic_mapping_status"], "unavailable")
        self.assertEqual(result["tactics"], [])
        self.assertEqual(result["renderer"]["renderer_id"], "watercolor-monk")
        self.assertEqual(result["renderer"]["result"], "observed")

    def test_exact_plans_aggregate_tactic_scores_without_guessing(self):
        decision = pw.build_decision(
            snapshots=[snapshot(i, click=i) for i in range(10)],
            observed_at="2026-08-02T06:00:00Z", product_id="ebook-ja",
            platform="tiktok", renderer_id="watercolor-monk")
        plans = [
            {"experiment_id": f"experiment.{i:024x}",
             "tactic_id": "tactic.low.v1" if i < 5 else "tactic.high.v1"}
            for i in range(10)
        ]
        result = pw.build_entity_performance(decision, experiment_plans=plans)
        self.assertEqual(result["tactic_mapping_status"], "available")
        tactics = {row["tactic_id"]: row for row in result["tactics"]}
        self.assertEqual(tactics["tactic.low.v1"]["result"], "lost")
        self.assertEqual(tactics["tactic.high.v1"]["result"], "won")
        self.assertEqual(tactics["tactic.low.v1"]["observations"], 5)


if __name__ == "__main__":
    unittest.main()
