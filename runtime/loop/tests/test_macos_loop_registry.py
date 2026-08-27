import json
import unittest
from pathlib import Path

from runtime.loop.macos_loop_registry import render_job_models, validate_registry


ROOT = Path(__file__).resolve().parents[3]


def entry(label="ai.anicca.example"):
    return {
        "label": label,
        "domain": "system",
        "entrypoint": "bin/example.sh",
        "cadence": {"run_at_load": True},
        "effect_class": "none",
        "state_root": "~/.local/state/life-manager/example",
        "log_root": "~/.local/state/life-manager/example/logs",
        "cleanup": {"max_runs": 10, "max_age_days": 7},
        "provider_route": "deterministic",
    }


class MacosLoopRegistryTest(unittest.TestCase):
    def test_registry_rejects_missing_and_secret_fields(self):
        missing = {"schema_version": 2, "loops": {"example": entry()}}
        del missing["loops"]["example"]["cleanup"]
        with self.assertRaisesRegex(ValueError, "cleanup"):
            validate_registry(missing)

        secret = {"schema_version": 2, "loops": {"example": entry()}}
        secret["loops"]["example"]["auth_token"] = "not-a-real-secret"
        with self.assertRaisesRegex(ValueError, "secret-like"):
            validate_registry(secret)

    def test_render_is_byte_stable_for_loop_insertion_order(self):
        left = {"schema_version": 2, "loops": {"b": entry("ai.anicca.b"), "a": entry("ai.anicca.a")}}
        right = {"schema_version": 2, "loops": {"a": entry("ai.anicca.a"), "b": entry("ai.anicca.b")}}
        self.assertEqual(render_job_models(left), render_job_models(right))

    def test_registry_covers_every_active_owned_inventory_label(self):
        registry = json.loads((ROOT / "config/loop-registry.json").read_text())
        inventory = json.loads((ROOT / "docs/evidence/runtime/2026-08-28-macos-loop-control-plane-inventory.json").read_text())
        validate_registry(registry)
        expected = {
            row["label"] for row in inventory["labels"]
            if row["installed"] and row["owner"] == "life-manager"
            and row["launchd_state"].startswith("loaded")
        }
        self.assertEqual({row["label"] for row in registry["loops"].values()}, expected)
        self.assertEqual(registry["loops"]["pm-live-trade"]["effect_class"], "trade")
        self.assertEqual(registry["loops"]["life-manager-payout"]["effect_class"], "money")
        self.assertEqual(registry["loops"]["life-manager-honne-ja"]["effect_class"], "publish")
        self.assertEqual(registry["loops"]["agentmail-replier"]["domain"], "earn")
        self.assertEqual(registry["loops"]["phone-conversation"]["domain"], "physical")
        self.assertEqual(registry["loops"]["x-repost"]["label"], "ai.anicca.x-repost-pass")
        self.assertEqual(registry["loops"]["x-tweeter"]["label"], "ai.anicca.x-tweeter-pass")

    def test_production_render_matches_byte_stable_fixture(self):
        registry = json.loads((ROOT / "config/loop-registry.json").read_text())
        expected = (ROOT / "runtime/loop/tests/fixtures/macos-loop-jobs.json").read_bytes()
        self.assertEqual(render_job_models(registry), expected)


if __name__ == "__main__":
    unittest.main()
