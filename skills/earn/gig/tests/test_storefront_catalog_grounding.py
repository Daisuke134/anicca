"""CREATE grounds its proposal in the owner's curated listing catalog, not invented content."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import storefront_direct  # noqa: E402


def test_catalog_entries_load_keyed_by_capability_family(tmp_path):
    catalog = {
        "listings": [
            {"id": "a", "family": "mvp_web_app_build", "title_ja": "t", "value_prop": "v",
             "tiers": [], "deliverables": ["d"], "required_inputs": ["r"], "faq": []},
            {"id": "b", "family": "", "title_ja": "skip"},
        ]
    }
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(catalog), encoding="utf-8")
    entries = storefront_direct._load_catalog_entries(path)
    assert set(entries) == {"mvp_web_app_build"}
    assert entries["mvp_web_app_build"]["id"] == "a"


def test_missing_catalog_file_returns_empty_without_raising(tmp_path):
    assert storefront_direct._load_catalog_entries(tmp_path / "missing.json") == {}


def test_create_prompt_instructs_grounding_only_when_entry_present():
    demand = {"evidence_path": "/tmp/demand.json"}
    prompt_with, _ = storefront_direct._create_proposal_prompt(
        {"service_id": "1", "service_version_sha256": "a" * 64}, "mvp_web_app_build", {},
        demand, set(), [], listing_catalog_entry={"deliverables": ["x"]},
    )
    prompt_without, _ = storefront_direct._create_proposal_prompt(
        {"service_id": "1", "service_version_sha256": "a" * 64}, "mvp_web_app_build", {},
        demand, set(), [], listing_catalog_entry=None,
    )
    assert "owner_listing_catalog_entry" in prompt_with
    assert "owner_listing_catalog_entry is the owner's pre-decided spec" in prompt_with
    assert "owner_listing_catalog_entry is the owner's pre-decided spec" not in prompt_without
