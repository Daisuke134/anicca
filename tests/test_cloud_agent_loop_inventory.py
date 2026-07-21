#!/usr/bin/env python3
"""Current contract for the TODO #1 loop inventory refresh."""

from __future__ import annotations

import csv
import copy
import hashlib
import subprocess
import unittest
from collections import Counter
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
GENERATOR = REPO / "scripts/generate-cloud-agent-loop-inventory.py"
TRACKED = REPO / "docs/reference/cloud-agent-loop-inventory.tsv"
DOCUMENTATION = REPO / "docs/reference/cloud-agent-loop-inventory.md"
NEW_LAUNCHD_IDS = {
    "launchd:ai.anicca.article-d7d8-finalizer",
    "launchd:ai.anicca.article-zenn-retry",
    "launchd:ai.anicca.hf-gig-pass",
    "launchd:ai.anicca.orca-zenn-finalizer",
}
BASELINE_ID_COUNT = 330
BASELINE_ID_DIGEST = "e2aede36d9868eea8360dbac948271ecf1553fac28535362ff4d00152ff224e4"
EXPECTED_STATE_TRANSITIONS = {
    "launchd:ai.anicca.capafy-goal-monitor": "installed_not_loaded",
    "launchd:ai.anicca.capafy-ig-marketing-daily": "installed_not_loaded",
    "launchd:ai.anicca.disk-autoprune": "disabled_by_launchctl",
    "launchd:com.anicca.disk-cleaner": "disabled_by_launchctl",
}


def validate_inventory_identity(rows: list[dict[str, str]]) -> None:
    """Reject any removal/substitution from the reviewed 330-ID baseline."""
    ids = {row["inventory_id"] for row in rows}
    if len(rows) != 334 or len(ids) != 334 or not NEW_LAUNCHD_IDS <= ids:
        raise AssertionError("loop inventory identity mismatch")
    baseline_ids = sorted(ids - NEW_LAUNCHD_IDS)
    baseline_digest = hashlib.sha256(
        ("\n".join(baseline_ids) + "\n").encode()
    ).hexdigest()
    if len(baseline_ids) != BASELINE_ID_COUNT or baseline_digest != BASELINE_ID_DIGEST:
        raise AssertionError("reviewed baseline loop identity mismatch")


def rows_from_text(value: str) -> list[dict[str, str]]:
    return list(csv.DictReader(value.splitlines(), delimiter="\t"))


class LoopInventoryRefreshContractTests(unittest.TestCase):
    def test_tracked_inventory_has_exact_current_counts_and_new_launchd_rows(self) -> None:
        rows = rows_from_text(TRACKED.read_text(encoding="utf-8"))
        validate_inventory_identity(rows)
        self.assertEqual(334, len(rows))
        self.assertEqual(len(rows), len({row["inventory_id"] for row in rows}))
        self.assertTrue(all(all(row.values()) for row in rows))
        self.assertEqual(
            Counter({"launchd": 107, "openclaw_cron": 222, "railway_entrypoint": 1, "repository_entrypoint": 4}),
            Counter(row["source_type"] for row in rows),
        )
        self.assertTrue(NEW_LAUNCHD_IDS <= {row["inventory_id"] for row in rows})

    def test_exact_current_state_transitions_are_fixed(self) -> None:
        rows = rows_from_text(TRACKED.read_text(encoding="utf-8"))
        by_id = {row["inventory_id"]: row for row in rows}
        self.assertEqual(
            EXPECTED_STATE_TRANSITIONS,
            {inventory_id: by_id[inventory_id]["state"] for inventory_id in EXPECTED_STATE_TRANSITIONS},
        )

    def test_old_id_removal_and_addition_substitution_is_rejected(self) -> None:
        rows = rows_from_text(TRACKED.read_text(encoding="utf-8"))
        baseline_index = next(
            index for index, row in enumerate(rows)
            if row["inventory_id"] not in NEW_LAUNCHD_IDS
        )
        mutated = copy.deepcopy(rows)
        replacement = dict(mutated[baseline_index])
        replacement["inventory_id"] = "launchd:fixture-substitution"
        mutated[baseline_index] = replacement
        with self.assertRaises(AssertionError):
            validate_inventory_identity(mutated)

    def test_live_a_b_are_byte_exact_with_tracked(self) -> None:
        first = subprocess.run(
            ["python3", str(GENERATOR)], cwd=REPO, capture_output=True, text=True, check=True
        ).stdout
        second = subprocess.run(
            ["python3", str(GENERATOR)], cwd=REPO, capture_output=True, text=True, check=True
        ).stdout
        self.assertEqual(first, second)
        self.assertEqual(TRACKED.read_text(encoding="utf-8"), first)

    def test_tracked_inventory_keeps_payload_and_private_path_boundary(self) -> None:
        content = TRACKED.read_text(encoding="utf-8")
        self.assertNotIn("/Users/", content)
        self.assertNotIn("EnvironmentVariables", content)
        self.assertNotIn("PRIVATE_BODY_MUST_NOT_APPEAR", content)
        self.assertNotIn("\tprompt\t", content.lower())
        self.assertTrue(DOCUMENTATION.is_file())


if __name__ == "__main__":
    unittest.main()
