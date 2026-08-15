"""Test-session defaults for the gig loop.

★ The only job of this file is to guarantee that no test can spend money. ★

``scripts/artifact_judge.py`` runs a real provider through ``agent_runner.py`` from inside
``validate_paid_work``, which a large part of the paid-work suite reaches. Left alone,
running ``pytest tests`` would start ``codex exec`` once per affected test.

So every test gets a stub runner and a private, per-test verdict cache. A test that wants
a different answer sets ``GIG_ARTIFACT_JUDGE_STUB`` (see
``tests/fixtures/artifact_judge_stub_runner.py`` for the vocabulary); a test that wants to
prove what happens with no judge at all clears ``GIG_ARTIFACT_JUDGE_RUNNER`` itself.

★ Note what this masks, deliberately. ★ The stub answers ``deliverable`` by default, so a
regression that unhooked the judge entirely would still leave these tests green. The
things that actually pin the wiring are the explicit tests in
``tests/test_artifact_judge.py`` -- they clear or repoint these variables, and they assert
both that the gate refuses and that the two production call sites pass a judge in.
"""

from __future__ import annotations

from pathlib import Path

import pytest

STUB_RUNNER = Path(__file__).resolve().parent / "fixtures" / "artifact_judge_stub_runner.py"
# E1 (predelivery_score.py) shells out to agent_runner.py exactly like artifact_judge does,
# on its own env vars -- so it needs the identical never-spend-money default, or a test that
# reaches the delivery gate without explicitly stubbing the score would start a real provider.
SCORE_STUB_RUNNER = Path(__file__).resolve().parent / "fixtures" / "predelivery_score_stub_runner.py"


@pytest.fixture(autouse=True)
def _artifact_judge_never_calls_a_provider(monkeypatch, tmp_path):
    monkeypatch.setenv("GIG_ARTIFACT_JUDGE_RUNNER", str(STUB_RUNNER))
    # Per test, not shared: the cache is content-addressed, so a suite-wide directory
    # would replay one test's stubbed answer into the next test's identical fixture bytes.
    monkeypatch.setenv("GIG_ARTIFACT_JUDGE_STATE", str(tmp_path / "artifact-judge-state"))
    monkeypatch.delenv("GIG_ARTIFACT_JUDGE_STUB", raising=False)
    monkeypatch.setenv("GIG_PREDELIVERY_SCORE_RUNNER", str(SCORE_STUB_RUNNER))
    monkeypatch.setenv("GIG_PREDELIVERY_SCORE_STATE", str(tmp_path / "predelivery-score-state"))
    monkeypatch.delenv("GIG_PREDELIVERY_SCORE_STUB", raising=False)
    # ★ A11: no test may read the live pass evidence either. ★
    # ``artifact_judge.order_label_text`` recovers the marketplace order label from the
    # queue item gig_pass.sh hands the delivery browsers,
    # ``$GIG_EVIDENCE_ROOT/gig-pass-*/paid-queue-expected.json``. Left unset that is
    # ~/gig/evidence -- 61 real pass directories at 08:56 on 2026-08-08, 35 of them holding
    # a queue item for a paying customer, and the tree is GC'd so it refills. A fixture
    # project whose directory name happened to equal a live request id would then be judged
    # against a real buyer's order, and every test that builds an order would walk the live
    # tree.
    # Same rule as the cache above: per test, private, and empty unless the test fills it.
    monkeypatch.setenv("GIG_EVIDENCE_ROOT", str(tmp_path / "pass-evidence"))
