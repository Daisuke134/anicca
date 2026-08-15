#!/usr/bin/env python3
"""A rejected pass must change the next pass's prompt instead of repeating into it.

2026-08-07 12:41, order 91000002: the buyer asked 「どちらを確認すればよいでしょうか？」, the
classifier called it a revision, delivery_action became work_required, and the work gate
says an artifact is the only legal output under work_required. So the builder wrapped its
answer inside a file -- artifacts/delivery-v3.md, a document explaining how to open the
document you are reading. The pass rejected it, quarantined it, and one hour later handed
the next builder a byte-identical prompt. That loop is what kept this order alive for five
days in its previous form.

The parent does not diagnose the order here and never writes a BLOCKED record on the
builder's behalf. It repeats three things it recorded itself: which attempt failed, the
reason it recorded, and that nothing reached the buyer.
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1]
FUNCTION = "paid_work_prior_rejection_clause"
MARKER = "You are the high-value paid-work builder."
PROJECT = "/workspace/gig/projects/91000002"


def _source() -> list[str]:
    return (SKILL / "gig_pass.sh").read_text(encoding="utf-8").splitlines()


def _function(name: str) -> str:
    """The shipped function body, verbatim -- not a copy of it kept in the test."""
    collected: list[str] = []
    for line in _source():
        if not collected:
            if line.startswith(f"{name}() {{"):
                collected.append(line)
            continue
        collected.append(line)
        if line == "}":
            return "\n".join(collected)
    raise AssertionError(f"{name} was not found in gig_pass.sh")


def _line_containing(needle: str) -> str:
    for line in _source():
        if needle in line:
            return line.strip()
    raise AssertionError(f"no line of gig_pass.sh contains {needle!r}")


def _home(tmp_path: Path, ledgers: list[dict], label: str = "h") -> Path:
    home = tmp_path / f"home-{label}"
    for index, ledger in enumerate(ledgers):
        directory = home / "gig" / "evidence" / f"gig-pass-{index}"
        directory.mkdir(parents=True)
        (directory / "paid-work-transaction.json").write_text(
            json.dumps(ledger, ensure_ascii=False), encoding="utf-8")
    home.mkdir(parents=True, exist_ok=True)
    return home


def _run(script: str, home: Path) -> str:
    done = subprocess.run(
        ["bash", "-c", script], capture_output=True, text=True, check=False,
        env={**os.environ, "HOME": str(home)},
    )
    assert done.returncode == 0, done.stderr
    return done.stdout


def _clause(tmp_path: Path, ledgers: list[dict], project: str = PROJECT, label: str = "h") -> str:
    home = _home(tmp_path, ledgers, label)
    script = f"{_function(FUNCTION)}\n{FUNCTION} {shlex.quote(project)}\n"
    return _run(script, home)


def _rejected_ledger(*, reason: str, stamp: str, project: str = PROJECT) -> dict:
    """The shape the live ledger actually had after the 12:41 rejection."""
    return {
        "version": 1,
        "status": "rolled_back",
        "project_root": project,
        "started_at": stamp,
        "finished_at": stamp,
        "failure_reason": reason,
        "quarantined": [
            {"kind": "artifact",
             "from": f"{project}/artifacts/delivery-v3.md",
             "to": "/workspace/gig/evidence/gig-pass-1786074007-75714/rejected-output/artifact--delivery-v3.md"},
            {"kind": "acceptance", "from": f"{project}/acceptance/acceptance-v3.json", "to": "x"},
        ],
    }


@pytest.mark.parametrize(
    "reason",
    ["answer_forbidden_stale_blocked_record", "answer_forbidden_for_work_required"],
)
def test_a_rejected_pass_is_carried_into_the_next_prompt(tmp_path, reason):
    clause = _clause(tmp_path, [_rejected_ledger(reason=reason, stamp="2026-08-07T03:45:53Z")])
    assert "PREVIOUS PASS REJECTED, NOTHING REACHED THE BUYER" in clause
    # The concrete thing that must not be produced again, named from the ledger.
    assert "delivery-v3.md" in clause
    assert reason in clause
    # And the legal move it was told to make instead.
    assert "acceptance-blocked.json" in clause
    assert "SHA256" in clause


def test_the_stale_case_says_the_record_was_about_older_feedback(tmp_path):
    """Absent and stale are different situations; the clause has to say which one happened."""
    stale = _clause(tmp_path, [_rejected_ledger(
        reason="answer_forbidden_stale_blocked_record", stamp="2026-08-07T03:45:53Z")],
        label="stale")
    assert "古い買い手フィードバック" in stale
    absent = _clause(tmp_path, [_rejected_ledger(
        reason="answer_forbidden_for_work_required", stamp="2026-08-07T03:45:53Z")],
        label="absent")
    assert "古い買い手フィードバック" not in absent


def test_a_rejection_a_later_pass_superseded_stops_steering(tmp_path):
    """Otherwise one bad hour would shout at every builder this project ever gets."""
    clause = _clause(tmp_path, [
        _rejected_ledger(reason="answer_forbidden_stale_blocked_record",
                         stamp="2026-08-07T03:45:53Z"),
        {"version": 1, "status": "promoted", "project_root": PROJECT,
         "finished_at": "2026-08-07T05:00:00Z"},
    ])
    assert clause.strip() == ""


def test_the_passes_own_in_flight_ledger_does_not_mask_the_last_rejection(tmp_path):
    """Measured live 2026-08-07 13:01, on the first pass that ran this code.

    paid_work_transaction begin writes this pass's own ledger before the builder prompt is
    assembled, so the newest ledger for the project is always the pass doing the asking --
    still active, finished_at null, failure_reason null. Reading it as "the last attempt"
    swallowed the 12:41 rejection whole and the clause came out empty. Only an attempt that
    ended has an outcome to carry forward.
    """
    clause = _clause(tmp_path, [
        _rejected_ledger(reason="answer_forbidden_stale_blocked_record",
                         stamp="2026-08-07T03:45:53Z"),
        {"version": 1, "status": "active", "project_root": PROJECT,
         "started_at": "2026-08-07T04:01:40.242144+00:00",
         "finished_at": None, "failure_reason": None},
    ], label="inflight")
    assert "PREVIOUS PASS REJECTED, NOTHING REACHED THE BUYER" in clause
    assert "delivery-v3.md" in clause


def test_another_projects_rejection_is_not_borrowed(tmp_path):
    clause = _clause(tmp_path, [_rejected_ledger(
        reason="answer_forbidden_stale_blocked_record", stamp="2026-08-07T03:45:53Z",
        project="/workspace/gig/projects/9999999")])
    assert clause.strip() == ""


def test_a_clean_project_gets_no_clause(tmp_path):
    clause = _clause(tmp_path, [
        {"version": 1, "status": "promoted", "project_root": PROJECT,
         "finished_at": "2026-08-07T05:00:00Z"},
    ])
    assert clause.strip() == ""


def test_a_corrupt_ledger_is_skipped_not_fatal(tmp_path):
    home = _home(tmp_path, [_rejected_ledger(
        reason="answer_forbidden_stale_blocked_record", stamp="2026-08-07T03:45:53Z")])
    broken = home / "gig" / "evidence" / "gig-pass-broken"
    broken.mkdir(parents=True)
    (broken / "paid-work-transaction.json").write_text("{not json", encoding="utf-8")
    script = f"{_function(FUNCTION)}\n{FUNCTION} {shlex.quote(PROJECT)}\n"
    assert "PREVIOUS PASS REJECTED" in _run(script, home)


def test_the_work_required_gate_still_refuses_when_nothing_says_we_are_blocked():
    """The escape hatch stays an exception: no BLOCKED record, no answer, no send.

    The refusal split two situations into two names this pass, so the proof that the
    original refusal is untouched runs here too rather than only in the shell suite. That
    script extracts the guard verbatim out of gig_pass.sh, so it cannot drift from what
    ships, and its cases 4 and 5 are exactly "absent must refuse" and "fresh may answer".
    """
    done = subprocess.run(
        ["bash", str(SKILL / "tests" / "test_gig_paid_work_required_no_send.sh")],
        capture_output=True, text=True, check=False,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert "work_required answers only when the builder is blocked on the current feedback" \
        in done.stdout


def test_the_clause_reaches_the_prompt_the_model_actually_reads(tmp_path):
    """The whole point is the next builder's input, so assert on the rendered prompt.

    Both the wiring line and the prompt argument are taken verbatim out of gig_pass.sh: a
    clause that is built but never joined to feedback_clause must not be able to pass.
    """
    home = _home(tmp_path, [_rejected_ledger(
        reason="answer_forbidden_stale_blocked_record", stamp="2026-08-07T03:45:53Z")])
    prompt_argument = _line_containing(MARKER).rstrip("\\").strip()
    script = "\n".join((
        _function(FUNCTION),
        f'TOP_PROJECT_ROOT={shlex.quote(PROJECT)}; SCHEMA="/tmp/schema.json"',
        'trusted_clause=""; paid_domain_skills=""; builder_queue_json="{}"',
        'feedback_clause=""',
        # Verbatim: a clause that is built and never joined must not be able to pass here.
        _line_containing(f"$({FUNCTION}"),
        f'printf "%s\\n" {prompt_argument}',
    ))
    rendered = _run(script, home)
    assert MARKER in rendered
    assert "PREVIOUS PASS REJECTED, NOTHING REACHED THE BUYER" in rendered
    assert "delivery-v3.md" in rendered
