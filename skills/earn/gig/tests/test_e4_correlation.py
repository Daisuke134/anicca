"""E4 (26-gig-loop §CC'/§EW' item 4): does E1's predelivery score predict what E2/the
classifier later recorded?
Run directly: python3 skills/earn/gig/tests/test_e4_correlation.py
(NEVER pytest -- the rtk shim blocks it, see repo convention in sibling tests).
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("e4_correlation", SCRIPTS / "e4_correlation.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _score(project_dir: Path, score: int, scored_at: float) -> None:
    _write_json(project_dir / "acceptance" / "predelivery-score.json", {
        "score": score, "dimensions": [{"name": "x", "score": score, "reason": "r"}],
        "scored_at": scored_at, "model": "gig-PREDELIVERY-SCORE", "floor": 40,
    })


def test_project_with_score_and_post_score_reaction_joins():
    tmp = Path(tempfile.mkdtemp())
    try:
        projects_root = tmp / "projects"
        project_dir = projects_root / "91000002"
        _score(project_dir, 85, 100.0)
        _write_json(project_dir / "state.json", {"talkroom_id": "90000002"})
        outcomes = tmp / "buyer-outcomes.jsonl"
        _write_jsonl(outcomes, [
            {"ts": 50, "talkroom_id": "90000002", "project_id": "91000002", "text": "before", "reaction": "neutral"},
            {"ts": 200, "talkroom_id": "90000002", "project_id": "91000002", "text": "great", "reaction": "positive"},
        ])
        out_path = tmp / "score-reality.jsonl"

        summary = MODULE.correlate(projects_root, outcomes, out_path)

        assert summary["scored_projects"] == 1, summary
        assert summary["joined"] == 1, summary
        rows = _read_jsonl(out_path)
        assert len(rows) == 1
        row = rows[0]
        assert row["project_id"] == "91000002"
        assert row["talkroom_id"] == "90000002"
        assert row["score"] == 85
        assert row["first_reaction"] == "positive"  # the only >= scored_at candidate
        assert row["reaction_ts"] == 200
        assert row["scored_ts"] == 100.0
        print("PASS test_project_with_score_and_post_score_reaction_joins")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_no_score_yet_yields_zero_joins():
    tmp = Path(tempfile.mkdtemp())
    try:
        projects_root = tmp / "projects"
        project_dir = projects_root / "1"
        _write_json(project_dir / "state.json", {"talkroom_id": "1"})
        outcomes = tmp / "buyer-outcomes.jsonl"
        _write_jsonl(outcomes, [{"ts": 10, "talkroom_id": "1", "project_id": "1", "text": "x", "reaction": "positive"}])
        out_path = tmp / "score-reality.jsonl"

        summary = MODULE.correlate(projects_root, outcomes, out_path)

        assert summary["scored_projects"] == 0, summary
        assert summary["joined"] == 0, summary
        assert not out_path.exists()
        print("PASS test_no_score_yet_yields_zero_joins")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_score_without_any_classified_reaction_is_skipped():
    tmp = Path(tempfile.mkdtemp())
    try:
        projects_root = tmp / "projects"
        project_dir = projects_root / "2"
        _score(project_dir, 60, 100.0)
        outcomes = tmp / "buyer-outcomes.jsonl"
        _write_jsonl(outcomes, [{"ts": 200, "talkroom_id": "2", "project_id": "2", "text": "?", "reaction": None}])
        out_path = tmp / "score-reality.jsonl"

        summary = MODULE.correlate(projects_root, outcomes, out_path)

        assert summary["scored_projects"] == 1, summary
        assert summary["joined"] == 0, summary
        print("PASS test_score_without_any_classified_reaction_is_skipped")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_reaction_before_score_is_not_used():
    tmp = Path(tempfile.mkdtemp())
    try:
        projects_root = tmp / "projects"
        project_dir = projects_root / "3"
        _score(project_dir, 60, 100.0)
        outcomes = tmp / "buyer-outcomes.jsonl"
        _write_jsonl(outcomes, [{"ts": 50, "talkroom_id": "3", "project_id": "3", "text": "old", "reaction": "positive"}])
        out_path = tmp / "score-reality.jsonl"

        summary = MODULE.correlate(projects_root, outcomes, out_path)

        assert summary["joined"] == 0, "a pre-score reaction must not be joined"
        print("PASS test_reaction_before_score_is_not_used")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_dedupe_on_second_run_over_same_state():
    tmp = Path(tempfile.mkdtemp())
    try:
        projects_root = tmp / "projects"
        project_dir = projects_root / "4"
        _score(project_dir, 90, 100.0)
        outcomes = tmp / "buyer-outcomes.jsonl"
        _write_jsonl(outcomes, [{"ts": 200, "talkroom_id": "4", "project_id": "4", "text": "x", "reaction": "positive"}])
        out_path = tmp / "score-reality.jsonl"

        first = MODULE.correlate(projects_root, outcomes, out_path)
        second = MODULE.correlate(projects_root, outcomes, out_path)

        assert first["joined"] == 1, first
        assert second["joined"] == 0, second
        assert second["skipped_existing"] == 1, second
        assert len(_read_jsonl(out_path)) == 1
        print("PASS test_dedupe_on_second_run_over_same_state")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_rescored_project_joins_again_as_a_second_delivery():
    tmp = Path(tempfile.mkdtemp())
    try:
        projects_root = tmp / "projects"
        project_dir = projects_root / "5"
        _score(project_dir, 50, 100.0)
        outcomes = tmp / "buyer-outcomes.jsonl"
        _write_jsonl(outcomes, [{"ts": 150, "talkroom_id": "5", "project_id": "5", "text": "revise", "reaction": "revision_request"}])
        out_path = tmp / "score-reality.jsonl"
        MODULE.correlate(projects_root, outcomes, out_path)

        # Revision delivered, re-scored later, and the buyer replies again.
        _score(project_dir, 90, 300.0)
        _write_jsonl(outcomes, [
            {"ts": 150, "talkroom_id": "5", "project_id": "5", "text": "revise", "reaction": "revision_request"},
            {"ts": 350, "talkroom_id": "5", "project_id": "5", "text": "good now", "reaction": "positive"},
        ])
        summary = MODULE.correlate(projects_root, outcomes, out_path)

        assert summary["joined"] == 1, summary
        rows = _read_jsonl(out_path)
        assert len(rows) == 2
        assert {r["scored_ts"] for r in rows} == {100.0, 300.0}
        print("PASS test_rescored_project_joins_again_as_a_second_delivery")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_null_score_record_is_not_joined():
    tmp = Path(tempfile.mkdtemp())
    try:
        projects_root = tmp / "projects"
        project_dir = projects_root / "6"
        _write_json(project_dir / "acceptance" / "predelivery-score.json", {
            "score": None, "dimensions": [], "scored_at": 100.0, "model": "x", "floor": 40,
        })
        outcomes = tmp / "buyer-outcomes.jsonl"
        _write_jsonl(outcomes, [{"ts": 200, "talkroom_id": "6", "project_id": "6", "text": "x", "reaction": "positive"}])
        out_path = tmp / "score-reality.jsonl"

        summary = MODULE.correlate(projects_root, outcomes, out_path)

        assert summary["scored_projects"] == 0, "a null score is not a determinate score"
        assert summary["joined"] == 0, summary
        print("PASS test_null_score_record_is_not_joined")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_missing_projects_root_and_malformed_score_file_do_not_crash():
    tmp = Path(tempfile.mkdtemp())
    try:
        summary = MODULE.correlate(tmp / "no-such-dir", tmp / "no-outcomes.jsonl", tmp / "out.jsonl")
        assert summary["joined"] == 0, summary

        projects_root = tmp / "projects"
        (projects_root / "7" / "acceptance").mkdir(parents=True)
        (projects_root / "7" / "acceptance" / "predelivery-score.json").write_text("{not json", encoding="utf-8")
        summary2 = MODULE.correlate(projects_root, tmp / "no-outcomes.jsonl", tmp / "out2.jsonl")
        assert summary2["scored_projects"] == 0, summary2
        print("PASS test_missing_projects_root_and_malformed_score_file_do_not_crash")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    test_project_with_score_and_post_score_reaction_joins()
    test_no_score_yet_yields_zero_joins()
    test_score_without_any_classified_reaction_is_skipped()
    test_reaction_before_score_is_not_used()
    test_dedupe_on_second_run_over_same_state()
    test_rescored_project_joins_again_as_a_second_delivery()
    test_null_score_record_is_not_joined()
    test_missing_projects_root_and_malformed_score_file_do_not_crash()
    print("ALL PASS")
