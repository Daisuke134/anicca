"""A family with a filled, unpublished draft is finished before any new demand cluster starts.

Draft 4387924 ("LINE公式アカウントの予約・定型応答を構築します", capability family `line_bot_dev`,
Y100,000) sat filled and unpublished for hours on the live account while
`_next_unused_demand_cluster` kept landing on other families with nothing built yet -- an
unpublished draft earns nothing, and finishing one already started is always worth more than
starting another.

This tests `_select_demand_cluster_for_wake`, the override that runs before
`_next_unused_demand_cluster` is allowed to decide, and `_families_with_unpublished_drafts`, the
generalised form of `_family_has_unpublished_draft` it is built on -- see
test_storefront_strike_keeps_live_draft.py for that helper's own tests, which this file must not
duplicate.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

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


def _cluster(family: str, *, score: int, status: str = "known", cluster_key: str | None = None) -> dict:
    return {
        "cluster_key": cluster_key or f"cluster:{family}",
        "query": f"query for {family}",
        "capability_family": family,
        "status": status,
        "score": score,
    }


LINE_DRAFT = {"draft_service_id": "4387924", "capability_family": "line_bot_dev",
              "status": "draft_created", "public_effect": 0}


# --- 1. no draft in flight -> normal choice unchanged -----------------------------------


def test_no_draft_in_flight_leaves_the_normal_choice_unchanged(tmp_path):
    state = _ledger(tmp_path, [])
    clusters = [_cluster("line_bot_dev", score=10), _cluster("excel_vba", score=50)]
    stranded = direct._families_with_unpublished_drafts(state, set())
    assert stranded == {}
    chosen, derivation = direct._select_demand_cluster_for_wake(clusters, set(), stranded)
    assert chosen == direct._next_unused_demand_cluster(clusters, set())
    assert chosen["capability_family"] == "excel_vba"
    assert derivation["reason"] == "unused_demand_cluster_available"


# --- 2 & 3. a draft in flight wins over a higher-scoring cluster -------------------------


def test_draft_created_family_is_selected_over_a_higher_scoring_cluster(tmp_path):
    state = _ledger(tmp_path, [LINE_DRAFT])
    clusters = [_cluster("line_bot_dev", score=10), _cluster("excel_vba", score=50)]
    stranded = direct._families_with_unpublished_drafts(state, set())
    assert stranded == {"line_bot_dev": ("4387924", 0)}
    chosen, derivation = direct._select_demand_cluster_for_wake(clusters, set(), stranded)
    assert chosen["capability_family"] == "line_bot_dev"
    assert derivation["reason"] == "unpublished_draft_awaiting_publication"
    assert derivation["unpublished_draft_service_id"] == "4387924"


def test_prepared_family_is_selected_over_a_higher_scoring_cluster(tmp_path):
    row = {**LINE_DRAFT, "status": "prepared"}
    state = _ledger(tmp_path, [row])
    clusters = [_cluster("line_bot_dev", score=10), _cluster("excel_vba", score=50)]
    stranded = direct._families_with_unpublished_drafts(state, set())
    chosen, derivation = direct._select_demand_cluster_for_wake(clusters, set(), stranded)
    assert chosen["capability_family"] == "line_bot_dev"
    assert derivation["reason"] == "unpublished_draft_awaiting_publication"
    assert derivation["unpublished_draft_service_id"] == "4387924"


# --- 4. two families in flight -> the oldest draft wins, deterministically ---------------


def test_two_families_in_flight_the_oldest_draft_wins(tmp_path):
    # excel_vba's draft is written first, line_bot_dev's second -- excel_vba has waited
    # longer even though line_bot_dev's cluster scores higher.
    excel_row = {"draft_service_id": "1111", "capability_family": "excel_vba",
                 "status": "draft_created", "public_effect": 0}
    state = _ledger(tmp_path, [excel_row, LINE_DRAFT])
    clusters = [_cluster("line_bot_dev", score=50), _cluster("excel_vba", score=10)]
    stranded = direct._families_with_unpublished_drafts(state, set())
    assert set(stranded) == {"excel_vba", "line_bot_dev"}
    chosen, derivation = direct._select_demand_cluster_for_wake(clusters, set(), stranded)
    assert chosen["capability_family"] == "excel_vba"
    assert derivation["unpublished_draft_service_id"] == "1111"

    # Same two drafts, reversed write order -> line_bot_dev is now the older one and wins.
    state2 = _ledger(tmp_path.with_name(tmp_path.name + "-2"), [LINE_DRAFT, excel_row])
    stranded2 = direct._families_with_unpublished_drafts(state2, set())
    chosen2, derivation2 = direct._select_demand_cluster_for_wake(clusters, set(), stranded2)
    assert chosen2["capability_family"] == "line_bot_dev"
    assert derivation2["unpublished_draft_service_id"] == "4387924"


# --- 5. a draft exists but no matching cluster is known -> no-op, not a new listing ------


def test_no_known_cluster_for_the_stranded_family_no_op_and_no_create(tmp_path):
    state = _ledger(tmp_path, [LINE_DRAFT])
    clusters = [_cluster("excel_vba", score=50)]  # nothing known for line_bot_dev
    stranded = direct._families_with_unpublished_drafts(state, set())
    chosen, derivation = direct._select_demand_cluster_for_wake(clusters, set(), stranded)
    assert chosen is None
    assert derivation["selected_cluster"] is None
    assert derivation["selected_score"] is None
    assert derivation["reason"] == "unpublished_draft_awaiting_known_cluster"
    assert derivation["unpublished_draft_service_id"] == "4387924"
    # With no cluster chosen, run_once's cluster-driven create path never builds a blueprint --
    # asserted against the source so a future edit that decouples the two silently regresses.
    source = (SCRIPTS / "storefront_direct.py").read_text(encoding="utf-8")
    assert ("if (unused_cluster is not None and bound_category is not None\n"
            "                    and unsold_family is None and not family_already_public):") in source


# --- 6. public or deleted drafts do not count as in flight -------------------------------


def test_a_public_draft_does_not_count_as_in_flight(tmp_path):
    state = _ledger(tmp_path, [LINE_DRAFT])
    stranded = direct._families_with_unpublished_drafts(state, {"4387924"})
    assert stranded == {}
    clusters = [_cluster("line_bot_dev", score=10), _cluster("excel_vba", score=50)]
    chosen, derivation = direct._select_demand_cluster_for_wake(clusters, set(), stranded)
    assert chosen["capability_family"] == "excel_vba"
    assert derivation["reason"] == "unused_demand_cluster_available"


def test_a_deleted_draft_does_not_count_as_in_flight(tmp_path, monkeypatch):
    state = _ledger(tmp_path, [LINE_DRAFT])
    monkeypatch.setattr(direct, "_observed_deleted_draft_ids", lambda evidence_root: {"4387924"})
    stranded = direct._families_with_unpublished_drafts(state, set())
    assert stranded == {}


# --- 7. demand_derivation names the override; a normal pick never carries that reason ----


def test_normal_selection_never_carries_the_override_reason_or_draft_id(tmp_path):
    state = _ledger(tmp_path, [])
    clusters = [_cluster("excel_vba", score=50)]
    stranded = direct._families_with_unpublished_drafts(state, set())
    _, derivation = direct._select_demand_cluster_for_wake(clusters, set(), stranded)
    assert derivation["reason"] == "unused_demand_cluster_available"
    assert "unpublished_draft_service_id" not in derivation


def test_no_cluster_and_no_stranded_draft_is_a_plain_no_op(tmp_path):
    state = _ledger(tmp_path, [])
    stranded = direct._families_with_unpublished_drafts(state, set())
    chosen, derivation = direct._select_demand_cluster_for_wake([], set(), stranded)
    assert chosen is None
    assert derivation is None


# --- a dismissed cluster whose draft is real: the draft wins, and that is recorded -------


def test_a_dismissed_cluster_still_wins_when_its_family_has_a_real_draft(tmp_path):
    state = _ledger(tmp_path, [LINE_DRAFT])
    clusters = [_cluster("line_bot_dev", score=10, cluster_key="cluster:line_bot_dev")]
    stranded = direct._families_with_unpublished_drafts(state, set())
    chosen, derivation = direct._select_demand_cluster_for_wake(
        clusters, {"cluster:line_bot_dev"}, stranded)
    assert chosen is not None and chosen["capability_family"] == "line_bot_dev"
    assert derivation["reason"] == "unpublished_draft_awaiting_publication"
    assert derivation["overrides_dismissal"] is True
