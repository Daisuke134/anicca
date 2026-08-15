import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = "https://coconala.com/requests?sort=new&recruiting=true"
sys.path.insert(0, str(ROOT / "scripts"))


def load(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_direct_newest_entry_points_use_official_recruiting_source():
    parent = load("application_parent")
    objective = load("b2_search_objective")
    gate = load("b2_result_gate")

    assert parent.CdpSnapshotCollector._source_url("single:new") == CANONICAL
    assert objective._WAKE_REFRESH_CURSOR["next_url"] == CANONICAL
    assert objective._MARKET_REFRESH_CURSOR["next_url"] == CANONICAL
    assert gate._missing_required_source_url("single:new") == CANONICAL


def test_legacy_newest_cursor_migrates_to_filtered_page_one_and_keeps_ids():
    objective = load("b2_search_objective")
    legacy = {
        "source_id": "single:new",
        "previous_url": "https://coconala.com/requests?page=46&sort=new",
        "next_url": "https://coconala.com/requests?page=47&sort=new",
        "reason": "next_page",
        "prior_inspected_request_ids": ["42", "42", "01KYKDECET9WAY0CKRBCKH81RC"],
    }

    assert objective._validated_cursor(legacy) == {
        "source_id": "single:new",
        "previous_url": "",
        "next_url": CANONICAL,
        "reason": "recruiting_filter_migration",
        "prior_inspected_request_ids": ["42", "01KYKDECET9WAY0CKRBCKH81RC"],
    }


def test_filtered_newest_cursor_resumes_and_malformed_variants_fail_closed():
    objective = load("b2_search_objective")
    canonical = {
        "source_id": "single:new",
        "previous_url": f"{CANONICAL}&page=3",
        "next_url": f"{CANONICAL}&page=4",
        "reason": "next_page",
    }

    assert objective._validated_cursor(canonical) == canonical
    for invalid in (
        "https://coconala.com/requests?page=47&sort=new&extra=1",
        f"{CANONICAL}&page=0",
        f"{CANONICAL}&page=01",
    ):
        with pytest.raises(ValueError, match="cursor_next_url_invalid"):
            objective._validated_cursor({**canonical, "next_url": invalid})
