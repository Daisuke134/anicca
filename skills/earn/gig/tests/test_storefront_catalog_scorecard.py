"""Contract tests for the versioned Storefront catalog scorecard."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCORECARD = ROOT / "config" / "storefront-catalog-scorecard.json"
sys.path.insert(0, str(ROOT / "scripts"))
from storefront_direct import MEASURABLE_SUCCESS_METRICS  # noqa: E402
DIMENSIONS = (
    "demand",
    "outcome",
    "proof",
    "scope",
    "package",
    "intake",
    "image",
    "repeat",
)
EXPECTED_SCORES = {
    "91000001": [2, 2, 1, 2, 1, 2, 0, 0],
    "91000005": [2, 2, 1, 1, 2, 2, 1, 1],
    "4244912": [1, 2, 1, 1, 2, 2, 1, 0],
    "4302213": [1, 1, 1, 2, 1, 2, 1, 0],
    "4330753": [1, 2, 1, 1, 1, 2, 0, 2],
    "4330105": [1, 2, 1, 2, 1, 2, 0, 0],
    "91000002": [2, 2, 1, 1, 2, 2, 1, 1],
    "4244556": [1, 2, 1, 1, 1, 2, 1, 2],
    "4313100": [2, 2, 1, 2, 1, 2, 1, 0],
    "4312985": [2, 2, 1, 1, 1, 2, 1, 0],
    "91000004": [2, 1, 1, 1, 2, 1, 1, 0],
}
EXPECTED_IMAGE_COUNTS = {
    "91000001": 0, "91000005": 4, "4244912": 3, "4302213": 5,
    "4330753": 0, "4330105": 0, "91000002": 6, "4244556": 3,
    "4313100": 3, "4312985": 1, "91000004": 6,
}


def _load() -> dict:
    return json.loads(SCORECARD.read_text(encoding="utf-8"))


def test_catalog_has_verified_eleven_service_scorecards_and_policy():
    document = _load()
    assert document["schema_version"] == 1
    assert document["source_contract_path"] == "storefront-direct/offer-contracts.jsonl"
    assert document["dimensions"] == list(DIMENSIONS)

    services = document["services"]
    ids = [row["service_id"] for row in services]
    assert len(services) == len(EXPECTED_SCORES) == 11
    assert len(ids) == len(set(ids))
    assert set(ids) == set(EXPECTED_SCORES)

    for row in services:
        service_id = row["service_id"]
        assert row["public_url"] == f"https://coconala.com/services/{service_id}"
        assert isinstance(row["price_jpy"], int) and row["price_jpy"] > 0
        observation = row["observation"]
        assert observation["image_count"] == EXPECTED_IMAGE_COUNTS[service_id]
        assert observation["observed_at"].endswith("+00:00")
        assert len(observation["public_content_sha256"]) == 64
        int(observation["public_content_sha256"], 16)
        assert list(row["scores"]) == list(DIMENSIONS)
        assert [row["scores"][name] for name in DIMENSIONS] == EXPECTED_SCORES[service_id]
        assert list(row["evidence"]) == list(DIMENSIONS)
        for name in DIMENSIONS:
            assert isinstance(row["scores"][name], int)
            assert 0 <= row["scores"][name] <= 2
            assert isinstance(row["evidence"][name], str)
            assert len(row["evidence"][name].strip()) >= 20
        assert row["evidence"]["demand"].startswith("https://coconala.com/")

    backlog = document["priority_backlog"]
    priorities = [row["priority"] for row in backlog]
    # The backlog lists open gaps, so it shrinks when one is genuinely closed.
    assert priorities == list(range(1, len(backlog) + 1))
    assert len(priorities) == len(set(priorities))
    assert backlog
    assert {row["service_id"] for row in backlog} <= set(EXPECTED_SCORES)
    assert len({row["service_id"] for row in backlog}) == len(backlog)
    for row in backlog:
        assert row["field"] in DIMENSIONS
        service = next(item for item in services if item["service_id"] == row["service_id"])
        assert row["before"] == service["scores"][row["field"]]
        # Only metrics the loop can actually measure; a synthetic conversion ratio is not one.
        assert row["success_metric"] in MEASURABLE_SUCCESS_METRICS
        assert isinstance(row["reason"], str) and row["reason"].strip()
    assert priorities and priorities[0] == 1
    first = backlog[0]
    # The top item must be a real open gap with an evidence-backed reason. Naming a specific
    # service here is what went stale: 91000001/image was listed as "0 images" long after the
    # listing had one, and the adapter only refused it once the fence stopped hiding it.
    assert first["before"] < 2
    assert len(first["reason"].strip()) >= 20

    policy = document["new_slot_policy"]
    assert policy["all_required"] is True
    assert set(policy["required_evidence"]) == {
        "distinct_demand_evidence",
        "owned_capability_evidence",
    }
    assert policy["delivery_capacity_required"] is True
    assert policy["quota_can_authorize"] is False
    assert set(policy["forbidden_authority"]) == {"quota"}
