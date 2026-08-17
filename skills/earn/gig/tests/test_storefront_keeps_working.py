"""The loop must keep finding improvement work after its committed backlog is spent.

Run: python3 -m pytest skills/earn/gig/tests/test_storefront_keeps_working.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import storefront_direct as sd  # noqa: E402

SCORECARD = Path(__file__).resolve().parents[1] / "config" / "storefront-catalog-scorecard.json"
ALIAS = {"outcome": "title", "scope": "body"}


def versions():
    import json
    rows = json.loads(SCORECARD.read_text(encoding="utf-8"))["services"]
    return {str(row["service_id"]): "a" * 64 for row in rows}


def test_the_catalogue_itself_supplies_work_when_the_backlog_is_spent():
    candidate = sd._scorecard_gap_candidate(SCORECARD, versions(), set(), set(), ALIAS)
    assert candidate is not None
    assert candidate["before"] < 2
    assert ALIAS.get(candidate["field"], candidate["field"]) in sd.GENERATED_MUTATION_FIELDS


def test_an_untouched_gap_outranks_one_already_published():
    every = versions()
    first = sd._scorecard_gap_candidate(SCORECARD, every, set(), set(), ALIAS)
    pair = (first["service_id"], ALIAS.get(first["field"], first["field"]))
    # Scores are static config; once a field has been published the score no longer reflects
    # reality, so the loop must move on rather than rework the same field forever.
    second = sd._scorecard_gap_candidate(SCORECARD, every, set(), set(), ALIAS, done_pairs={pair})
    assert (second["service_id"], ALIAS.get(second["field"], second["field"])) != pair


def test_an_open_experiment_or_missing_version_blocks_a_gap():
    every = versions()
    first = sd._scorecard_gap_candidate(SCORECARD, every, set(), set(), ALIAS)
    blocked = sd._scorecard_gap_candidate(
        SCORECARD, every, {first["service_id"]}, set(), ALIAS)
    assert blocked is None or blocked["service_id"] != first["service_id"]
    assert sd._scorecard_gap_candidate(SCORECARD, {}, set(), set(), ALIAS) is None


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
