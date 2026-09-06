import json
import copy
import re
import time
import unittest
from pathlib import Path

from runtime.loop.macos_loop_registry import render_job_models, validate_registry
from runtime.loop.lm_loop import status_rows


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
    def test_boot_panic_evidence_runs_once_when_the_aqua_session_loads(self):
        registry = json.loads((ROOT / "config/loop-registry.json").read_text())
        self.assertEqual(registry["loops"]["boot-panic-evidence"], {
            "cadence": {"run_at_load": True},
            "cleanup": {"max_age_days": 30, "max_runs": 20},
            "domain": "system",
            "effect_class": "none",
            "entrypoint": "runtime/host/boot_panic_collector.py",
            "label": "ai.anicca.boot-panic-evidence",
            "log_root": "~/.local/state/life-manager/boot-panic-evidence/logs",
            "provider_route": "deterministic",
            "state_root": "~/.local/state/life-manager/boot-panic-evidence",
        })

    def test_money_printer_symphony_is_retired_after_cloud_cutover(self):
        registry = json.loads((ROOT / "config/loop-registry.json").read_text())
        self.assertNotIn("money-printer-symphony", registry["loops"])
        self.assertIn("ai.anicca.life-manager-money-printer-symphony", registry["retired_labels"])

    def test_money_printer_symphony_bridge_is_retired_after_cloud_cutover(self):
        registry = json.loads((ROOT / "config/loop-registry.json").read_text())
        self.assertNotIn("money-printer-symphony-bridge", registry["loops"])
        self.assertIn("ai.anicca.life-manager-money-printer-symphony-bridge", registry["retired_labels"])

    def test_legacy_telegram_bot_is_retired_after_gateway_cutover(self):
        registry = json.loads((ROOT / "config/loop-registry.json").read_text())
        self.assertNotIn("telegram-bot", registry["loops"])
        self.assertIn("ai.anicca.telegram-bot", registry["retired_labels"])

    def test_release_reconciler_is_an_independent_system_owner(self):
        registry = json.loads((ROOT / "config/loop-registry.json").read_text())
        row = registry["loops"]["life-manager-release-reconciler"]
        self.assertEqual(row, {
            "cadence": {"start_interval_seconds": 60},
            "cleanup": {"max_age_days": 14, "max_runs": 100},
            "domain": "system",
            "effect_class": "none",
            "entrypoint": "bin/reconcile-agent-runner-release.sh",
            "label": "ai.anicca.life-manager-release-reconciler",
            "log_root": "~/.local/state/life-manager/release-reconciler/logs",
            "provider_route": "deterministic",
            "state_root": "~/.local/state/life-manager/release-reconciler",
        })
        self.assertEqual(validate_registry(registry), registry)

    def test_release_reconciler_scopes_each_route_to_the_four_gig_owners(self):
        script = (ROOT / "bin/reconcile-agent-runner-release.sh").read_text()
        self.assertIn(
            "reconcile shared-agent-runner --loaded-idle-only "
            "--loop-id hf-gig-apply-direct",
            script,
        )
        self.assertIn(
            "reconcile shared-agent-runner --include-running "
            "--loop-id hf-gig-reply-detector",
            script,
        )
        self.assertIn(
            "reconcile deterministic --loaded-idle-only "
            "--loop-id hf-gig-storefront-direct --loop-id hf-gig-paid-direct "
            "--loop-id life-manager-disk-cleanup",
            script,
        )

    def test_registry_rejects_missing_and_secret_fields(self):
        missing = {"schema_version": 2, "loops": {"example": entry()}}
        del missing["loops"]["example"]["cleanup"]
        with self.assertRaisesRegex(ValueError, "cleanup"):
            validate_registry(missing)

        secret = {"schema_version": 2, "loops": {"example": entry()}}
        secret["loops"]["example"]["auth_token"] = "not-a-real-secret"
        with self.assertRaisesRegex(ValueError, "secret-like"):
            validate_registry(secret)

    def test_external_labels_are_explicit_and_cannot_overlap_managed(self):
        value = {"schema_version": 2, "loops": {"example": entry()},
                 "external_labels": ["ai.anicca.tsbridge"]}
        self.assertEqual(validate_registry(value), value)
        value["external_labels"] = ["ai.anicca.example"]
        with self.assertRaisesRegex(ValueError, "overlap"):
            validate_registry(value)

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
        expected -= set(registry.get("retired_labels", []))
        self.assertTrue(expected.issubset({row["label"] for row in registry["loops"].values()}))
        self.assertEqual(registry["loops"]["pm-live-trade"]["effect_class"], "trade")
        self.assertEqual(registry["loops"]["life-manager-payout"]["effect_class"], "money")
        self.assertEqual(registry["loops"]["life-manager-honne-ja"]["effect_class"], "publish")
        self.assertEqual(registry["loops"]["agentmail-replier"]["domain"], "earn")
        self.assertEqual(registry["loops"]["phone-conversation"]["domain"], "physical")
        self.assertEqual(registry["loops"]["x-repost"]["label"], "ai.anicca.x-repost-pass")
        self.assertEqual(registry["loops"]["x-tweeter"]["label"], "ai.anicca.x-tweeter-pass")
        self.assertEqual(registry["loops"]["x-tweeter"]["cadence"],
                         {"calendar_interval": {"Minute": 15}})

    def test_production_render_matches_byte_stable_fixture(self):
        registry = json.loads((ROOT / "config/loop-registry.json").read_text())
        expected = (ROOT / "runtime/loop/tests/fixtures/macos-loop-jobs.json").read_bytes()
        self.assertEqual(render_job_models(registry), expected)

    def test_loop_entrypoints_do_not_select_auth_or_codex_home(self):
        registry = json.loads((ROOT / "config/loop-registry.json").read_text())
        forbidden = re.compile(r"CODEX_HOME|auth\.json|AGENT_RUNNER_PROVIDER")
        violations = []
        for loop_id, entry in registry["loops"].items():
            path = ROOT / entry["entrypoint"]
            if path.is_file() and forbidden.search(path.read_text(errors="replace")):
                violations.append((loop_id, entry["entrypoint"]))
        self.assertEqual(violations, [])

    def test_active_entrypoints_do_not_depend_on_other_worktrees(self):
        registry = json.loads((ROOT / "config/loop-registry.json").read_text())
        forbidden = re.compile(r"/" + r"Users/[^/]+/.*(?:\.worktrees|/Projects/|/profitable-claude)")
        violations = []
        for loop_id, entry in registry["loops"].items():
            path = ROOT / entry["entrypoint"]
            if path.is_file() and forbidden.search(path.read_text(errors="replace")):
                violations.append((loop_id, entry["entrypoint"]))
        self.assertEqual(violations, [])

    def test_render_500_loops_and_status_under_five_seconds(self):
        base = entry()
        loops = {}
        for index in range(500):
            loop_id = f"scale-{index:03d}"
            row = copy.deepcopy(base)
            row["label"] = f"ai.anicca.{loop_id}"
            row["state_root"] = f"~/.local/state/life-manager/{loop_id}"
            row["log_root"] = f"~/.local/state/life-manager/{loop_id}/logs"
            loops[loop_id] = row
        registry = {"schema_version": 2, "loops": loops}

        started = time.perf_counter()
        rendered = render_job_models(registry)
        render_seconds = time.perf_counter() - started
        started = time.perf_counter()
        rows = status_rows(
            registry, loaded={}, disabled={}, events={}, installed_releases={})
        status_seconds = time.perf_counter() - started

        self.assertEqual((len(rendered.splitlines()), len(rows)), (1, 500))
        self.assertLess(render_seconds, 5)
        self.assertLess(status_seconds, 5)


if __name__ == "__main__":
    unittest.main()
