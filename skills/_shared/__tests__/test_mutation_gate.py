"""PROP-C3-mutation-gate (required:true, Tier 1 integration) — INV-10 fresh-context adversary.

Spec: REQ-C3 — strategy.json.next renames over strategy.json IFF
reviews/strategy-mutation-<sha>/verdict.json exists with overallVerdict=PASS.
"""
import json
import pytest

from lib.mutation_gate import apply_strategy_mutation  # FAIL until 2b


def _setup(tmp_path, verdict: dict | None):
    strategy = tmp_path / "strategy.json"
    strategy.write_text(json.dumps({"priority": ["A"]}))
    strategy_next = tmp_path / "strategy.json.next"
    strategy_next.write_text(json.dumps({"priority": ["B"]}))
    sha = "deadbeef" * 8
    reviews = tmp_path / "reviews" / f"strategy-mutation-{sha}" / "output"
    reviews.mkdir(parents=True)
    if verdict is not None:
        (reviews / "verdict.json").write_text(json.dumps(verdict))
    return strategy, strategy_next, sha, tmp_path / "lessons.jsonl"


# ── happy path: PASS verdict → rename happens ────────────────────────
def test_pass_verdict_renames_strategy_next_over_strategy(tmp_path):
    strategy, strategy_next, sha, lessons = _setup(
        tmp_path, {"overallVerdict": "PASS", "iteration": 1}
    )
    result = apply_strategy_mutation(
        slot_dir=tmp_path, strategy_path=strategy, next_path=strategy_next,
        sha=sha, lessons_path=lessons,
    )
    assert result.applied is True
    assert json.loads(strategy.read_text()) == {"priority": ["B"]}
    assert not strategy_next.exists()  # consumed


# ── FAIL verdict: do NOT rename, append lesson row ───────────────────
def test_fail_verdict_discards_next_and_logs_lesson(tmp_path):
    strategy, strategy_next, sha, lessons = _setup(
        tmp_path, {"overallVerdict": "FAIL", "iteration": 1,
                   "convergenceSignals": {"findingCount": 2}}
    )
    result = apply_strategy_mutation(
        slot_dir=tmp_path, strategy_path=strategy, next_path=strategy_next,
        sha=sha, lessons_path=lessons,
    )
    assert result.applied is False
    assert json.loads(strategy.read_text()) == {"priority": ["A"]}  # unchanged
    # lesson row appended
    rows = [json.loads(l) for l in lessons.read_text().splitlines() if l.strip()]
    assert len(rows) == 1
    assert rows[0]["category"] == "self-mutation"
    assert rows[0]["outcome"] == "mutation-rejected"


# ── verdict.json missing: treat as FAIL (= INV-10 fail-closed) ───────
def test_missing_verdict_treated_as_fail(tmp_path):
    strategy, strategy_next, sha, lessons = _setup(tmp_path, verdict=None)
    result = apply_strategy_mutation(
        slot_dir=tmp_path, strategy_path=strategy, next_path=strategy_next,
        sha=sha, lessons_path=lessons,
    )
    assert result.applied is False
    assert json.loads(strategy.read_text()) == {"priority": ["A"]}
