"""A three-strike skip must not throw away a draft that is already on the platform.

A new listing is built across more than one wake, because a wake spends exactly one effect:
the blank draft is created, then filled, then published. So a family can hold a real draft
while its most recent proposals are still being refused by a content guard. Dismissing its
demand cluster is permanent, so doing it then strands that draft and the work behind it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import storefront_direct as direct  # noqa: E402


def _ledger(tmp_path: Path, rows: list[dict]) -> Path:
    state = tmp_path / "state"
    (state / "evidence").mkdir(parents=True)
    with (state / "new-listing-drafts.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return state


def test_reports_a_created_draft_still_waiting_to_be_filled(tmp_path):
    state = _ledger(tmp_path, [
        {"draft_service_id": "4387924", "capability_family": "line_bot_dev",
         "status": "draft_created", "public_effect": 0},
    ])
    assert direct._family_has_unpublished_draft(state, "line_bot_dev", set()) == "4387924"


def test_reports_a_prepared_draft_too(tmp_path):
    state = _ledger(tmp_path, [
        {"draft_service_id": "4387924", "capability_family": "line_bot_dev",
         "status": "prepared", "public_effect": 0},
    ])
    assert direct._family_has_unpublished_draft(state, "line_bot_dev", set()) == "4387924"


@pytest.mark.parametrize("row, why", [
    ({"draft_service_id": "4387924", "capability_family": "line_bot_dev",
      "status": "published", "public_effect": 1}, "already published"),
    ({"draft_service_id": "4387924", "capability_family": "excel_vba",
      "status": "draft_created", "public_effect": 0}, "different family"),
    ({"draft_service_id": "notanid", "capability_family": "line_bot_dev",
      "status": "draft_created", "public_effect": 0}, "non-numeric id"),
])
def test_nothing_in_flight(tmp_path, row, why):
    state = _ledger(tmp_path, [row])
    assert direct._family_has_unpublished_draft(state, "line_bot_dev", set()) is None, why


def test_a_draft_that_went_public_is_not_in_flight(tmp_path):
    state = _ledger(tmp_path, [
        {"draft_service_id": "4387924", "capability_family": "line_bot_dev",
         "status": "draft_created", "public_effect": 0},
    ])
    assert direct._family_has_unpublished_draft(state, "line_bot_dev", {"4387924"}) is None


def test_missing_ledger_is_not_an_error(tmp_path):
    state = tmp_path / "state"
    state.mkdir()
    assert direct._family_has_unpublished_draft(state, "line_bot_dev", set()) is None


def test_dismissal_is_gated_on_having_nothing_in_flight():
    # The guard the production branch relies on, asserted against the source so a future edit
    # that drops the condition and goes back to dismissing unconditionally fails here.
    source = (SCRIPTS / "storefront_direct.py").read_text(encoding="utf-8")
    assert "if cluster_key and live_draft is None:" in source
    assert "_family_has_unpublished_draft(\n                        args.state_dir, create_family, inventory_ids)" in source
