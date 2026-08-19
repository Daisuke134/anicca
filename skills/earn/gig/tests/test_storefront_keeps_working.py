"""The loop must keep finding improvement work after its committed backlog is spent.

Run: python3 -m pytest skills/earn/gig/tests/test_storefront_keeps_working.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import storefront_direct as sd  # noqa: E402

ALIAS = {"outcome": "title", "scope": "body"}


def scorecard(tmp_path):
    path = tmp_path / "scorecard.json"
    path.write_text(json.dumps({"services": [
        {"service_id": "90000001", "scores": {"title": 0, "body": 1}},
        {"service_id": "90000002", "scores": {"title": 1, "body": 0}},
    ]}), encoding="utf-8")
    return path


def versions():
    return {"90000001": "a" * 64, "90000002": "b" * 64}


def test_the_catalogue_itself_supplies_work_when_the_backlog_is_spent(tmp_path):
    candidate = sd._scorecard_gap_candidate(scorecard(tmp_path), versions(), set(), set(), ALIAS)
    assert candidate is not None
    assert candidate["before"] < 2
    assert ALIAS.get(candidate["field"], candidate["field"]) in sd.GENERATED_MUTATION_FIELDS


def test_an_untouched_gap_outranks_one_already_published(tmp_path):
    every = versions()
    scorecard_path = scorecard(tmp_path)
    first = sd._scorecard_gap_candidate(scorecard_path, every, set(), set(), ALIAS)
    pair = (first["service_id"], ALIAS.get(first["field"], first["field"]))
    # Scores are static config; once a field has been published the score no longer reflects
    # reality, so the loop must move on rather than rework the same field forever.
    second = sd._scorecard_gap_candidate(scorecard_path, every, set(), set(), ALIAS, done_pairs={pair})
    assert (second["service_id"], ALIAS.get(second["field"], second["field"])) != pair


def test_an_open_experiment_or_missing_version_blocks_a_gap(tmp_path):
    every = versions()
    scorecard_path = scorecard(tmp_path)
    first = sd._scorecard_gap_candidate(scorecard_path, every, set(), set(), ALIAS)
    blocked = sd._scorecard_gap_candidate(
        scorecard_path, every, {first["service_id"]}, set(), ALIAS)
    assert blocked is None or blocked["service_id"] != first["service_id"]
    assert sd._scorecard_gap_candidate(scorecard_path, {}, set(), set(), ALIAS) is None


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
