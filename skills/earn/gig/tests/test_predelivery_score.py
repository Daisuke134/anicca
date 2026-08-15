"""E1 (26-gig-loop §CC' 段E): score the deliverable before the buyer sees it.

Two kinds of test, same split as ``test_artifact_judge.py``: fast ones that drive the real
subprocess boundary against ``predelivery_score_stub_runner.py`` (so the summary read, the
score parse and every fail-open/fail-closed path are exercised for real, at zero cost -- the
autouse fixture in ``conftest.py`` points every test at the stub already), and pure-function
tests of ``parse_score`` and ``score_predelivery``'s floor logic with an injected scorer.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import predelivery_score  # noqa: E402
import project_ledger  # noqa: E402


def _project(tmp_path: Path, buyer_text: str = "企画と台本を作ってください。締切は来週です。") -> Path:
    root = project_ledger.init_project(tmp_path, "9100001", "coconala")
    talkroom = root / "source" / "talkroom"
    talkroom.mkdir(parents=True, exist_ok=True)
    (talkroom / "messages.jsonl").write_text(
        json.dumps({"side": "buyer", "text": buyer_text}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return root


# ---------------------------------------------------------------------------
# parse_score: fails toward None, never toward a fabricated number
# ---------------------------------------------------------------------------

def test_parse_score_accepts_a_well_formed_payload():
    result = predelivery_score.parse_score(
        {"score": 72, "dimensions": [{"name": "scope_match", "score": 70, "reason": "ok"}]}
    )
    assert result == {"score": 72, "dimensions": [{"name": "scope_match", "score": 70, "reason": "ok"}]}


@pytest.mark.parametrize("payload", [
    None,
    [],
    "not a dict",
    {"score": "90", "dimensions": [{"name": "x", "score": 1, "reason": "r"}]},  # score not int
    {"score": True, "dimensions": [{"name": "x", "score": 1, "reason": "r"}]},  # bool is not int
    {"score": 140, "dimensions": [{"name": "x", "score": 1, "reason": "r"}]},  # out of range
    {"score": 50, "dimensions": []},  # empty dimensions
    {"score": 50, "dimensions": [{"name": "", "score": 1, "reason": "r"}]},  # blank name
    {"score": 50, "dimensions": [{"name": "x", "score": 999, "reason": "r"}]},  # dim out of range
    {"score": 50},  # dimensions missing entirely
])
def test_parse_score_rejects_to_none(payload):
    assert predelivery_score.parse_score(payload) is None


# ---------------------------------------------------------------------------
# run_score: real subprocess boundary against the stub runner
# ---------------------------------------------------------------------------

def test_run_score_high_via_stub_runner(tmp_path, monkeypatch):
    monkeypatch.setenv("GIG_PREDELIVERY_SCORE_STUB", "high")
    result = predelivery_score.run_score(
        "order text", tmp_path / "a.txt", "artifact body", "a.txt", 10,
        evidence_dir=tmp_path / "evidence",
    )
    assert result == {"score": 90, "dimensions": [{"name": "scope_match", "score": 90, "reason": "stub"}]}


def test_run_score_out_of_range_is_none(tmp_path, monkeypatch):
    monkeypatch.setenv("GIG_PREDELIVERY_SCORE_STUB", "out_of_range")
    result = predelivery_score.run_score(
        "order text", tmp_path / "a.txt", "artifact body", "a.txt", 10,
        evidence_dir=tmp_path / "evidence",
    )
    assert result is None


@pytest.mark.parametrize("stub_mode", ["crash", "malformed", "no_result"])
def test_run_score_provider_trouble_is_none_not_a_crash(tmp_path, monkeypatch, stub_mode):
    monkeypatch.setenv("GIG_PREDELIVERY_SCORE_STUB", stub_mode)
    result = predelivery_score.run_score(
        "order text", tmp_path / "a.txt", "artifact body", "a.txt", 10,
        evidence_dir=tmp_path / "evidence",
    )
    assert result is None


def test_run_score_missing_runner_is_none():
    result = predelivery_score.run_score(
        "order text", Path("a.txt"), "body", "a.txt", 10,
        runner=Path("/does/not/exist.py"), evidence_dir=Path("/tmp/unused-evidence"),
    )
    assert result is None


# ---------------------------------------------------------------------------
# default_scorer: reuses artifact_judge's own read of "what can be judged at all"
# ---------------------------------------------------------------------------

def test_default_scorer_skips_binary_artifacts(tmp_path, monkeypatch):
    monkeypatch.setenv("GIG_PREDELIVERY_SCORE_STUB", "high")
    root = _project(tmp_path)
    artifact = root / "artifacts" / "package.zip"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    # Not valid UTF-8 and not a real zip -- lands on "binary" in artifact_judge.artifact_body,
    # same as the real zip/mp4/png packages that are the overwhelming majority of live
    # artifacts (measured in artifact_judge.py).
    artifact.write_bytes(b"\xff\xd8\xff\xe0not a real jpeg either")
    assert predelivery_score.default_scorer(root, artifact) is None


def test_default_scorer_skips_when_no_order_text_on_record(tmp_path, monkeypatch):
    monkeypatch.setenv("GIG_PREDELIVERY_SCORE_STUB", "high")
    root = project_ledger.init_project(tmp_path, "9100002", "coconala")
    artifact = root / "artifacts" / "delivery.txt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("some prose", encoding="utf-8")
    assert predelivery_score.default_scorer(root, artifact) is None


def test_default_scorer_scores_a_readable_text_artifact(tmp_path, monkeypatch):
    monkeypatch.setenv("GIG_PREDELIVERY_SCORE_STUB", "high")
    root = _project(tmp_path)
    artifact = root / "artifacts" / "delivery.txt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("台本の第一稿です。", encoding="utf-8")
    result = predelivery_score.default_scorer(root, artifact)
    assert result == {"score": 90, "dimensions": [{"name": "scope_match", "score": 90, "reason": "stub"}]}


# ---------------------------------------------------------------------------
# score_predelivery: the floor, the evidence file, and the ledger line
# ---------------------------------------------------------------------------

def test_high_score_delivers_and_is_recorded(tmp_path):
    root = _project(tmp_path)
    artifact = root / "artifacts" / "delivery.txt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("stub artifact", encoding="utf-8")

    record = predelivery_score.score_predelivery(
        root, artifact, scorer=lambda *_a, **_k: {
            "score": 85, "dimensions": [{"name": "scope_match", "score": 85, "reason": "matches"}]
        },
    )

    assert record["score"] == 85
    evidence = json.loads((root / "acceptance" / "predelivery-score.json").read_text(encoding="utf-8"))
    assert evidence["score"] == 85
    state = json.loads((root / "state.json").read_text(encoding="utf-8"))
    assert state["predelivery_score"] == 85
    events = (root / "events.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(events[-1])["event"] == predelivery_score.LEDGER_EVENT


def test_low_score_raises_and_is_still_recorded(tmp_path):
    root = _project(tmp_path)
    artifact = root / "artifacts" / "delivery.txt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("stub artifact", encoding="utf-8")

    with pytest.raises(ValueError, match=predelivery_score.ERROR_PREDELIVERY_SCORE_LOW):
        predelivery_score.score_predelivery(
            root, artifact, scorer=lambda *_a, **_k: {
                "score": 15, "dimensions": [{"name": "scope_match", "score": 15, "reason": "wrong type"}]
            },
        )

    evidence = json.loads((root / "acceptance" / "predelivery-score.json").read_text(encoding="utf-8"))
    assert evidence["score"] == 15
    state = json.loads((root / "state.json").read_text(encoding="utf-8"))
    assert state["predelivery_score"] == 15


def test_score_exactly_on_the_floor_delivers(tmp_path):
    """The floor blocks *below*, not *at* -- an off-by-one here silently doubles the cutoff."""
    root = _project(tmp_path)
    artifact = root / "artifacts" / "delivery.txt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("stub artifact", encoding="utf-8")

    record = predelivery_score.score_predelivery(
        root, artifact, scorer=lambda *_a, **_k: {
            "score": predelivery_score.SCORE_FLOOR,
            "dimensions": [{"name": "scope_match", "score": predelivery_score.SCORE_FLOOR, "reason": "borderline"}],
        },
    )
    assert record["score"] == predelivery_score.SCORE_FLOOR


def test_scorer_failure_is_fail_open_not_fail_closed(tmp_path):
    """A scoring outage must not stop a delivery -- see the module docstring."""
    root = _project(tmp_path)
    artifact = root / "artifacts" / "delivery.txt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("stub artifact", encoding="utf-8")

    def broken_scorer(*_a, **_k):
        raise RuntimeError("provider unreachable")

    record = predelivery_score.score_predelivery(root, artifact, scorer=broken_scorer)
    assert record["score"] is None
    state = json.loads((root / "state.json").read_text(encoding="utf-8"))
    assert state["predelivery_score"] is None


def test_scorer_returning_none_is_also_fail_open(tmp_path):
    root = _project(tmp_path)
    artifact = root / "artifacts" / "delivery.txt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("stub artifact", encoding="utf-8")

    record = predelivery_score.score_predelivery(root, artifact, scorer=lambda *_a, **_k: None)
    assert record["score"] is None


def test_ledger_append_is_used_not_a_raw_state_write(tmp_path):
    """The record must be reachable only through project_ledger.append's audit trail."""
    root = _project(tmp_path)
    artifact = root / "artifacts" / "delivery.txt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("stub artifact", encoding="utf-8")
    before = (root / "events.jsonl").read_text(encoding="utf-8").splitlines()

    predelivery_score.score_predelivery(
        root, artifact, scorer=lambda *_a, **_k: {
            "score": 70, "dimensions": [{"name": "scope_match", "score": 70, "reason": "ok"}]
        },
    )

    after = (root / "events.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(after) == len(before) + 1
    row = json.loads(after[-1])
    assert row["state"]["predelivery_score"] == 70
    assert row["state"]["request_id"] == "9100001"  # merge preserved identity, did not clobber it
