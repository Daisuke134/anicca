from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


# 2026-08-06 12:00, caused by my own change: raising the application target to 8 lifted the
# ceiling in b2_result_gate and application_parent but not the two identical checks inside
# application_snapshot, so the very first pass after the raise died with
#
#     {"ok":false,"error":"objective_caps_invalid","error_at":"application_snapshot.py:304"}
#
# The number 7 was written in four places. A cap that lives in four files is not a contract,
# it is four opinions -- so the ceiling is one named constant and every check reads it.

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def collector(target: int, maximum: int) -> dict:
    return {
        "pass_id": "cap-test",
        "lease_fence": {"task": "cap-test", "token": "0" * 32, "generation": 1},
        "observed_at": "2026-08-06T12:00:00Z",
        "objective": {
            "target_applications": target,
            "max_applications": maximum,
            "required_search_source_ids": ["single:new"],
        },
        "search_sources": [{
            "source_id": "single:new",
            "url": "https://coconala.com/requests?sort=new",
            "page_index": 1,
            "card_request_ids": ["91000032"],
            "has_next": False,
            "exhausted": True,
            "screenshot_sha256": "a" * 64,
            "dom_sha256": "b" * 64,
        }],
        "request_details": [{
            "request_id": "91000032",
            "canonical_url": "https://coconala.com/requests/91000032",
            "title": "AI 調査",
            "category": "リサーチ",
            "visible_text": "募集内容",
            "accepting_applications": True,
            "budget_min_jpy": 1000,
            "budget_max_jpy": 5000,
            "applicants_count": 0,
            "contracted_count": 0,
            "observed_at": "2026-08-06T12:00:00Z",
        }],
        "already_applied_ids": [],
    }


def test_the_ceiling_is_one_named_constant() -> None:
    snapshot = load("application_snapshot_cap", "application_snapshot.py")
    parent = load("application_parent_cap", "application_parent.py")
    assert snapshot.MAX_APPLICATIONS_CEILING == 20
    # The parent contract must agree with the snapshot rather than carry its own number.
    assert parent.snapshot_contract.MAX_APPLICATIONS_CEILING == 20


def test_the_production_value_of_eight_is_accepted() -> None:
    snapshot = load("application_snapshot_cap8", "application_snapshot.py")
    envelope = snapshot.build_envelope(collector(8, 8))
    assert envelope["objective"]["target_applications"] == 8
    assert envelope["objective"]["max_applications"] == 8


def test_above_the_ceiling_is_still_refused() -> None:
    snapshot = load("application_snapshot_cap21", "application_snapshot.py")
    with pytest.raises(Exception, match="objective_caps_invalid"):
        snapshot.build_envelope(collector(8, 21))


def test_max_below_target_is_still_refused() -> None:
    snapshot = load("application_snapshot_capbad", "application_snapshot.py")
    with pytest.raises(Exception, match="objective_caps_invalid"):
        snapshot.build_envelope(collector(9, 8))
