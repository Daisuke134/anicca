import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("freeze-loop-inventory.py")
SPEC = importlib.util.spec_from_file_location("freeze_loop_inventory", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class FreezeLoopInventoryTest(unittest.TestCase):
    def test_builds_reproducible_projection_with_receipt_gaps_visible(self):
        registry = {
            "schema_version": 2,
            "loops": {
                "alpha": {"label": "ai.anicca.alpha"},
            },
            "external_labels": ["ai.anicca.external"],
            "retired_labels": ["ai.anicca.retired"],
        }
        adapters = {
            "schema_version": 1,
            "adapters": [{
                "adapter_id": "alpha-cloud",
                "loop_id": "alpha.cloud",
                "capability": "alpha.run",
                "effect_classes": ["money"],
                "module_ref": "lib/alpha.js",
                "factory_export": "createAlpha",
            }],
        }
        status = [
            {
                "classification": "managed",
                "owner": "life-manager",
                "loop_id": "alpha",
                "label": "ai.anicca.alpha",
                "last_pass": "2026-09-06T00:00:00Z",
                "last_terminal_result": "pass",
                "event_release_sha": "a" * 40,
                "effect_class": "money",
                "effect_status": "unknown",
            },
            {
                "classification": "external",
                "owner": "external",
                "loop_id": "ai.anicca.external",
                "label": "ai.anicca.external",
                "last_pass": None,
                "last_terminal_result": None,
                "event_release_sha": None,
                "effect_class": "unknown",
                "effect_status": "unknown",
            },
            {
                "classification": "retired",
                "owner": "retired",
                "loop_id": "ai.anicca.retired",
                "label": "ai.anicca.retired",
                "last_pass": None,
                "last_terminal_result": None,
                "event_release_sha": None,
                "effect_class": "unknown",
                "effect_status": "unknown",
            },
        ]

        projection = MODULE.build_projection(
            registry=registry,
            adapters=adapters,
            status=status,
            source_head="b" * 40,
            registry_sha256="c" * 64,
            adapters_sha256="d" * 64,
        )

        self.assertEqual(
            projection["counts"],
            {"managed": 1, "external": 1, "retired": 1, "cloud_adapters": 1},
        )
        row = projection["local_inventory"][0]
        self.assertEqual(row["owner"], "life-manager")
        self.assertEqual(row["last_terminal_receipt"]["result"], "pass")
        self.assertIsNone(row["official_effect_receipt"]["ref"])
        self.assertEqual(
            row["official_effect_receipt"]["reason"],
            "no_common_receipt_mapping",
        )
        self.assertEqual(projection["gaps"]["missing_terminal_receipts"], [])
        self.assertEqual(projection["gaps"]["unmapped_effect_receipts"], ["alpha"])
        self.assertEqual(projection["gaps"]["cloud_adapters_without_owner"], ["alpha-cloud"])

    def test_rejects_status_that_does_not_match_registry(self):
        with self.assertRaisesRegex(ValueError, "classification counts"):
            MODULE.build_projection(
                registry={"schema_version": 2, "loops": {"alpha": {}}, "external_labels": [], "retired_labels": []},
                adapters={"schema_version": 1, "adapters": []},
                status=[],
                source_head="a" * 40,
                registry_sha256="b" * 64,
                adapters_sha256="c" * 64,
            )

    def test_rejects_unmanaged_status_rows(self):
        with self.assertRaisesRegex(ValueError, "classification counts"):
            MODULE.build_projection(
                registry={"schema_version": 2, "loops": {}, "external_labels": [], "retired_labels": []},
                adapters={"schema_version": 1, "adapters": []},
                status=[{"classification": "unmanaged"}],
                source_head="a" * 40,
                registry_sha256="b" * 64,
                adapters_sha256="c" * 64,
            )


if __name__ == "__main__":
    unittest.main()
