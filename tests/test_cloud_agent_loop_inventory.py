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
CURRENT_ID_COUNT = 392
CURRENT_ID_DIGEST = "9f5479da29cb9159925166129606e6fa422b949faa6028d7267b961fba1209bb"
EXPECTED_STATE_TRANSITIONS = {
    "launchd:ai.anicca.capafy-goal-monitor": "loaded",
    "launchd:ai.anicca.capafy-ig-marketing-daily": "loaded",
    "launchd:ai.anicca.life-manager-selfbuild": "loaded",
    "launchd:ai.anicca.hf-gig-pass": "loaded",
    "launchd:com.anicca.disk-sentinel": "loaded",
}


def validate_inventory_identity(rows: list[dict[str, str]]) -> None:
    """Reject any removal, addition, or substitution from the reviewed current snapshot."""
    ids = sorted(row["inventory_id"] for row in rows)
    if len(rows) != CURRENT_ID_COUNT or len(set(ids)) != CURRENT_ID_COUNT:
        raise AssertionError("loop inventory identity mismatch")
    current_digest = hashlib.sha256(("\n".join(ids) + "\n").encode()).hexdigest()
    if current_digest != CURRENT_ID_DIGEST:
        raise AssertionError("reviewed current loop identity mismatch")


def rows_from_text(value: str) -> list[dict[str, str]]:
    return list(csv.DictReader(value.splitlines(), delimiter="\t"))


class LoopInventoryRefreshContractTests(unittest.TestCase):
    def test_tracked_inventory_has_exact_current_counts_and_identity(self) -> None:
        rows = rows_from_text(TRACKED.read_text(encoding="utf-8"))
        validate_inventory_identity(rows)
        self.assertEqual(CURRENT_ID_COUNT, len(rows))
        self.assertEqual(len(rows), len({row["inventory_id"] for row in rows}))
        self.assertTrue(all(all(row.values()) for row in rows))
        self.assertEqual(
            Counter({"launchd": 165, "openclaw_cron": 222, "railway_entrypoint": 1, "repository_entrypoint": 4}),
            Counter(row["source_type"] for row in rows),
        )

    def test_exact_current_state_transitions_are_fixed(self) -> None:
        rows = rows_from_text(TRACKED.read_text(encoding="utf-8"))
        by_id = {row["inventory_id"]: row for row in rows}
        self.assertEqual(
            EXPECTED_STATE_TRANSITIONS,
            {inventory_id: by_id[inventory_id]["state"] for inventory_id in EXPECTED_STATE_TRANSITIONS},
        )

    def test_current_id_removal_and_addition_substitution_is_rejected(self) -> None:
        rows = rows_from_text(TRACKED.read_text(encoding="utf-8"))
        mutated = copy.deepcopy(rows)
        replacement = dict(mutated[0])
        replacement["inventory_id"] = "launchd:fixture-substitution"
        mutated[0] = replacement
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
